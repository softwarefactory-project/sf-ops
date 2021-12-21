#!/bin/env python3

# Copyright 2021, Red Hat
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


import argparse

import kazoo.client
import kazoo.exceptions

parser = argparse.ArgumentParser(
    description="Clean ZK nodepool database tool."
    "For example: /zuul/events/connection/softwarefactory-project.io/events "
    "To get queue, you can use command: zkCli.sh ls /zuul/events/connection/"
)
parser.add_argument('--queue', help="provide path to the queue",
                    required=True)
parser.add_argument('--host', help="Specify zookeeper host",
                    default='zookeeper')
args = parser.parse_args()

client = kazoo.client.KazooClient(hosts=args.host)
client.start()

events = client.get_children(args.queue)
patches = list(map(lambda n: args.queue.rstrip("/") + "/" + n, events))
print("Current lenght of the queue %s is %s" % (args.queue, len(patches)))

for p in patches:
    try:
        client.delete(p)
    except kazoo.exceptions.NoNodeError:
        print("Can not remove %s" % p)
