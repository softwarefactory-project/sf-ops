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

# Usecase: When lot of instances are READY but LOCKED in Nodepool and uselessly eat tenant quota.
# This script detects READY nodes from the Zookeeper database, then filters by given arguments in
# order to delete nodes from the Openstack provider and the Zookeeper database.

import argparse
import os
import json
import time

import kazoo.client
import shade

parser = argparse.ArgumentParser(description="Clean ZK nodepool database tool")
parser.add_argument('--provider', help="only clean this provider")
parser.add_argument('--label', help="only clean this label")
parser.add_argument('--min-age', type=int, default=3 * 3600, help="minimum node age in seconds")
parser.add_argument('--dry', default=False, action='store_true', help="Do not write anything, dry run")
parser.add_argument('nodeid', nargs='*')
args = parser.parse_args()

max_age = time.time() - args.min_age
clouds = {}

client = kazoo.client.KazooClient(hosts="zookeeper")
client.start()

if not args.nodeid:
    args.nodeid = client.get_children("/nodepool/nodes")

for nodeid in args.nodeid:
    node_path = os.path.join("/nodepool/nodes", nodeid)
    if not client.exists(node_path):
        print("%s: doesn't exists" % node_path)
        continue
    node_data = client.get(node_path)[0].decode('utf-8')
    try:
        node = json.loads(node_data)
    except Exception as e:
        print("%s: decode failed (%s)" % (node_path, e))
        continue

    if node['state'] != 'ready':
        print("%s: skipping node state %s" % (node_path, node['state'])
        continue

    if node['state_time'] > max_age:
        print("%s: node too young" % node_path)
        continue

    cloud = node['provider']
    if args.provider and args.provider != cloud:
        print("%s: skipping filtered provider %" % (node_path, cloud))
        continue

    if args.label and args.label not in node['type']:
        print("%s: skipping filtered labels %s" % (node_path, node['type']))
        continue

    print()
    print("=" * 80)
    print("Name: %s" % node['hostname'])
    print("Age: %s" % (time.time() - node['state_time']))
    print("Label: %s" % node['type'])
    if cloud not in clouds:
        try:
            clouds[cloud] = shade.openstack_cloud(cloud=cloud)
        except:
            print("%s: couldn't get cloud" % cloud)
            continue
    print("%s: removing server %s" % (node_path, node['external_id']))
    try:
        if not args.dry:
            clouds[cloud].delete_server(node['external_id'])
        if False:
            print("%s: delete failed" % node['external_id'])
    except:
        print("%s: couldn't delete server" % node['external_id'])

    print("%s: removing..." % node_path)
    if not args.dry:
        client.delete(node_path, recursive=True)
    print()
