#!/opt/rh/rh-python35/root/usr/bin/python

import kazoo.client
import sys
import os.path

client = kazoo.client.KazooClient(hosts="zookeeper")
client.start()

def print_root(root):
    childs = client.get_children(root)
    for child in childs[:5]:
        print(os.path.join(root, child))
        print_root(os.path.join(root, child))

import argparse

p = argparse.ArgumentParser()
p.add_argument("--list", action="store_true")
p.add_argument("--deleting", action="store_true")
p.add_argument("--requesting", action="store_true")
args = p.parse_args()
import json

if args.list:
    print_root("/nodepool")
elif args.requesting:
    for req in client.get_children("/nodepool/requests"):
        req_path = os.path.join("/nodepool/requests", req)
        req = json.loads(client.get(req_path)[0].decode('utf-8'))
        if req["requestor"] == "NodePool:min-ready":
            print("Deleting %s" % req_path)
            client.delete(req_path, recursive=True)
elif args.deleting:
    for node in client.get_children("/nodepool/nodes"):
        node_path = os.path.join("/nodepool/nodes", node)
        node_data = client.get(node_path)[0].decode('utf-8')
        try:
            node = json.loads(node_data)
        except:
            print("%s: decode failed" % node_path)
            if not node_data:
                print("Deleting empty %s" % node_path)
                client.delete(node_path, recursive=True)
            else:
                print(node_data)
            continue
        if node["state"] == "deleting":
            print("Deleting %s" % node_path)
            client.delete(node_path, recursive=True)
        else:
            print(node_path, node["state"])
