#!/bin/env python3
# Copyright 2019, Red Hat
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


import sys
import kazoo.client

try:
    nodepath = sys.argv[1]
except IndexError:
    print("usage: %s zk-node-path" % sys.argv[0])
    exit(1)

client = kazoo.client.KazooClient(hosts="zookeeper")
client.start()

if nodepath.endswith('/'):
    print(client.get_children(nodepath))
else:
    print(client.get(nodepath))
