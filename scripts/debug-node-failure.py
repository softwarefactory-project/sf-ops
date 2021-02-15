#!/bin/env python3
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""This script looks for noderequest in zuul log and get the
   associated nodepool launcher logs"""

import time
import re
import argparse


def usage():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--change", required=True)
    parser.add_argument("--job", required=True)
    return parser.parse_args()


def print_nodepool_log(nodesets):
    with open("/var/log/nodepool/launcher.log") as nlog:
        while True:
            line = nlog.readline()
            if not line:
                break
            if any([nodeset in line for nodeset in nodesets]):
                print(line, end='')


def main():
    args = usage()
    regexp = re.compile("DEBUG zuul\.Pipeline\.[^:]+: .* "
                        "Adding node request <NodeRequest ([0-9-]+) .* for job "
                        + args.job + " to item .* " + args.project
                        + " " + args.change + ">")

    start = time.monotonic()
    idx = 0
    print("Looking for nodeset in scheduler log:")
    nodesets = []
    with open("/var/log/zuul/scheduler.log") as zlog:
        while True:
          line = zlog.readline()
          if not line:
            break
          match = regexp.match(line[24:])
          if match:
              print("Found nodeset: ", line, end='')
              print(match.groups()[0])
              nodesets.append(match.groups()[0])
          idx += 1
    stop = time.monotonic()
    print("It took %s for %d lines" % (stop - start, idx))

    print("Looking for nodeset in nodepool log:")
    print_nodepool_log(nodesets)
    

if __name__ == "__main__":
    main()
