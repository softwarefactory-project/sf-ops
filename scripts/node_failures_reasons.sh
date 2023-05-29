#!/bin/sh
#
# Copyright (C) 2023 Red Hat
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

# Use this script to weed through nodepool logs and display all error messages associated to node requests that ended in NODE_FAILURE.
# Useful for investigating "massive" node failures at once.

TODAY=$(date +%Y%m%d -d 'today')

# * Look for jobs ending in NODE_FAILUREs in the scheduler in the last day, take note of the associated node requests
FAILED_REQUESTS=$(cat /var/log/zuul/scheduler.log-$TODAY /var/log/zuul/scheduler.log | egrep -oh 'NODE_FAILURE Node request [0-9]+-[0-9]+' | sort | uniq | awk '{print $NF}' | tr '\n' '|' | sed 's/|$//')

# * Get every node ID associated with found node requests
FAILED_NODES=$(cat /var/log/nodepool/launcher.log-$TODAY /var/log/nodepool/launcher.log | egrep '('$FAILED_REQUESTS').+Launch failed for node' | awk '{print $NF}' | sed 's/:$//' | tr '\n' '|' | sed 's/|$//')

# * Print out nodepool error notifications associated with the node IDs -> can be shared with #help-it-cloud-openstack
cat /var/log/nodepool/launcher.log-$TODAY /var/log/nodepool/launcher.log | egrep '('$FAILED_NODES')' | grep -i ERROR