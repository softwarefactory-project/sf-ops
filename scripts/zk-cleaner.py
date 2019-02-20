#!/bin/env python3

# Copyright 2018, Red Hat
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Usecase:
# When lot of instances are in a stale state ['ready', 'aborted', 'deleting', 'failed']
# for a while (default 3hrs) and usually LOCKED in Nodepool and by effect uselessly eat tenant quota.
# This script detects these nodes from the Zookeeper database, then filters by given arguments and
# tries to delete nodes from the Openstack provider and the Zookeeper database.

import argparse
import os
import json
import time

import kazoo.client
import shade

parser = argparse.ArgumentParser(description="Clean ZK nodepool database tool")
parser.add_argument('--provider', help="only clean this provider")
parser.add_argument('--label', help="only clean this label")
parser.add_argument('--min-age', type=int, default=24 * 3600,
                    help="minimum node age in seconds")
parser.add_argument('--dry', default=False, action='store_true',
                    help="Do not write anything, dry run")
parser.add_argument('--requests', action='store_true',
                    help="clean requests list instead")
parser.add_argument('nodeid', nargs='*')
args = parser.parse_args()

now = time.time()
max_age = time.time() - args.min_age
clouds = {}

client = kazoo.client.KazooClient(hosts="zookeeper")
client.start()

base_path = "/nodepool/nodes"
if args.requests:
    base_path = "/nodepool/requests"

if not args.nodeid:
    args.nodeid = client.get_children(base_path)


for nodeid in sorted(args.nodeid):
    node_path = os.path.join(base_path, nodeid)
    print("\n===> %s <===" % node_path)
    if not client.exists(node_path):
        print("Node path doesn't exists")
        continue

    node_zk = client.get(node_path)
    node_age = now - node_zk[1].mtime / 1000
    if node_age < args.min_age:
        print("Skipping recent node (%d)" % node_age)
        continue

    if args.requests:
        lock_path = os.path.join("/nodepool/requests-lock", nodeid)
    else:
        lock_path = os.path.join("/nodepool/nodes/lock", nodeid)
    if client.exists(lock_path):
        lock_zk = client.get(lock_path)
        lock_age = now - lock_zk[1].mtime / 1000
        if lock_age < args.min_age:
            print("Skipping recent lock (%d)" % lock_age)
            continue
    else:
        lock_path = None

    node_data = node_zk[0].decode('utf-8')
    try:
        node = json.loads(node_data)
    except json.decoder.JSONDecodeError as e:
        print("Removing node because decode fail '%s' (%s)" % (node_data, e))
        if not args.dry:
            if lock_path:
                client.delete(lock_path, recursive=True)
            client.delete(node_path, recursive=True)
        continue

    if node['state'] in ('in-use',):
        print("Skipping node state %s" % node['state'])
        continue

    if node['state_time'] > max_age:
        print("Skipping recent node state time (%d)" % node['state_time'])
        continue

    if args.requests:
        print("Removing request ZK node from %s..." %
              time.ctime(node['state_time']))
        if not args.dry:
            client.delete(node_path, recursive=True)
            if lock_path and client.exists(lock_path):
                client.delete(lock_path, recursive=True)
        continue

    provider = node['provider']
    if args.provider and args.provider != provider:
        print("Skipping filtered provider %s" % provider)
        continue

    if args.label and args.label not in node['type']:
        print("Skipping filtered labels %s" % node['type'])
        continue

    print("Name: %s" % node['hostname'])
    print("Age: %s" % (time.time() - node['state_time']))
    print("Label: %s" % node['type'])
    print("Provider: %s" % node['provider'])
    print("Pool: %s" % node['pool'])
    print("State: %s" % node['state'])
    if provider not in clouds:
        try:
            clouds[provider] = shade.openstack_cloud(cloud=provider)
        except Exception:
            print("Couldn't get cloud client")
            clouds[provider] = None

    if clouds[provider]:
        print("Removing cloud server %s" % node['external_id'])
        try:
            if not args.dry:
                ret = clouds[provider].delete_server(node['external_id'], force=True)
            if not ret:
                print("%s: delete failed" % node['external_id'])
        except Exception:
            print("%s: couldn't delete server" % node['external_id'])

    print("Removing the ZK node...")
    if not args.dry:
        client.delete(node_path, recursive=True)
        if lock_path and client.exists(lock_path):
            client.delete(lock_path, recursive=True)
