#!/bin/env python3
# Copyright 2020, Red Hat
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

# A library to interact with zookeeper
# 
# Examples:
## Get client
# zk = client("zookeeper")
## Remove a single node
# delete_zkpath(zk, "/nodepool/nodes/0000081444")
## Get nodes of a providers:
# runc = filter_by_provider("managed-runc-provider")(get_nodes(zk))
## Get nodes path
# print(get_paths(runc))
## Delete nodes
# list(map(delete_zknode(zk), get_paths(runc)))

from pathlib import Path
import time
import json
import kazoo.client

def client(host):
    client = kazoo.client.KazooClient(hosts=host)
    client.start()
    return client

def decode_zknode(node_data):
    try:
        return json.loads(node_data[0])
    except Exception as e:
        print("%s: failed to decode: %s" % (e, node_data))
        return None

def delete_zkpath(client, zk_path):
    zk_path_str = str(zk_path)
    if client.exists(zk_path_str):
        print("%s: deleting" % zk_path_str)
        client.delete(zk_path_str, recursive=True)
    
def delete_zknode(client):
    def _func(node_path):
        lock_path = Path("/nodepool/nodes/lock") / node_path.name
        delete_zkpath(client, lock_path)
        delete_zkpath(client, node_path)
        return True
    return _func

def get_paths(tuple_list):
    return list(map(lambda x: x[0], tuple_list))

def get_nodes(client):
    base = Path("/nodepool/nodes")
    return list(filter(lambda x: x[1] is not None, [
        (base / node, decode_zknode(client.get(str(base / node))))
        for node in client.get_children(str(base))
    ]))

def filter_by_provider(name):
    def _func(nodes):
        return list(filter(lambda x: x[1]['provider'] == name, nodes))
    return _func

def order_by_age(tuple_list):
    return list(sorted(tuple_list, key=lambda t: t[1]['state_time']))

def format_state_time(tuple_list):
    return ["%s: %s" % (node_path, time.ctime(zk_node['state_time']))
            for (node_path, zk_node) in tuple_list]
                        
