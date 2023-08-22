#!/bin/env python3
# Copyright (C) 2023 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
This script process a nodepool launcher.log file to extract
some informations.
"""

import re
from collections import namedtuple

class Assign:
    regex = re.compile(".* nodepool.PoolWorker\..*: \[e: ([^\]]+)\] \[node_request: ([^\]]+)\] Assigning node request .* 'node_types': \[([^\]]+)\].* 'tenant_name': '([^']+)'.* 'pipeline_name': '([^']+)'.* 'job_name': '([^']+)'")
    mk_tuple = namedtuple('LaunchAssign', ['event', 'request', 'labels', 'tenant', 'pipeline', 'job'])

class Failure:
    regex = re.compile(".*\.StateMachineNodeLauncher\.([^:]+): \[e: ([^\]]+)\] \[node_request: ([^\]]+)\] \[node: ([^\]]+)\] Launch failed for node")
    mk_tuple = namedtuple('Failed', ['provider', 'event', 'request', 'node'])

def test_re():
    assign = try_match(Assign, "2023-08-22 16:11:13,558 INFO nodepool.PoolWorker.vexxhost-nodepool-tripleo-main: [e: 6699adb7f26d45e58b9b306cf5004b95] [node_request: 200-0006304754] Assigning node request <NodeRequest {'state': 'requested', 'state_time': 1692720656.8029158, 'declined_by': ['zs.softwarefactory-project.io-PoolWorker.k1s03-main-cf5c3441f3764532b106be493e40b0cd', 'ibm-bm3-nodepool-launcher.softwarefactory-project.io-PoolWorker.ibm-bm3-nodepool-main-2a314fc4bc06472faee9884acb411c9a', 'zs.softwarefactory-project.io-PoolWorker.managed-k1s-provider-k1s02-main-4ec436d92e9f447f8ad7c5a5947960e8', 'zs.softwarefactory-project.io-PoolWorker.sf-container-worker-1-main-2be7d6aa8ec44efdbfdd95479720851a', 'zs.softwarefactory-project.io-PoolWorker.vexxhost-nodepool-sf-main-628a91aca88746e89a744808735ca996', 'zs.softwarefactory-project.io-PoolWorker.ansible-vexxhost-sjc1-main-f99fdf7e67ac4a02921152b046ebb7a4', 'zs.softwarefactory-project.io-PoolWorker.ansible-vexxhost-ca-ymq-1-main-9920ddf0f8e8485aa7e93ed8b284e96f', 'zs.softwarefactory-project.io-PoolWorker.ansible-us-east-2-main-ab8d7cc2a53245109fcf174ff5e3aa1b', 'zs.softwarefactory-project.io-PoolWorker.ansible-vexxhost-ams1-main-7939788b96034d589b7cdafcc07f08cd', 'zs.softwarefactory-project.io-PoolWorker.k1s04-main-f0bc9a3c84e84732acaf4dc909c8c8f2'], 'node_types': ['cloud-centos-9-stream-tripleo-vexxhost'], 'nodes': [], 'reuse': True, 'requestor': '19a2731d0c454791bc3839ceb267d3e6', 'requestor_data': {'build_set_uuid': '4ab419b4ed8c4ec9bd3eaa4e6b26c37a', 'tenant_name': 'rdoproject.org', 'pipeline_name': 'openstack-promote-component', 'job_name': 'periodic-tripleo-centos-9-wallaby-component-compute-promote-to-promoted-components', 'span_info': {'name': 'RequestNodes', 'trace_id': 325643531921636611799219878427226861421, 'span_id': 4715787825685598036, 'trace_flags': 1, 'start_time': 1692720647805223680, 'parent': {'trace_id': 325643531921636611799219878427226861421, 'span_id': 4862299592563865637, 'is_remote': True}}}, 'provider': None, 'relative_priority': 0, 'event_id': '6699adb7f26d45e58b9b306cf5004b95', 'created_time': 1692720647.8052237, 'tenant_name': 'rdoproject.org', 'id': '200-0006304754', 'stat': ZnodeStat(czxid=4477220369, mzxid=4477221714, ctime=1692720647805, mtime=1692720656806, version=10, cversion=0, aversion=0, ephemeralOwner=0, dataLength=1943, numChildren=0, pzxid=4477220369)}>")
    assert assign == Assign.mk_tuple(event='6699adb7f26d45e58b9b306cf5004b95', request='200-0006304754', labels="'cloud-centos-9-stream-tripleo-vexxhost'", tenant='rdoproject.org', pipeline='openstack-promote-component', job='periodic-tripleo-centos-9-wallaby-component-compute-promote-to-promoted-components')
    match = try_match(Failure, "2023-08-22 14:07:38,345 ERROR nodepool.StateMachineNodeLauncher.ansible-us-east-2: [e: 14e75f705eee483bbe5c722ce1e7ddd8] [node_request: 300-0006199348] [node: 0003985405] Launch failed for node 0003985405:")
    assert match == ('ansible-us-east-2', '14e75f705eee483bbe5c722ce1e7ddd8', '300-0006199348', '0003985405')
    assert match.provider == 'ansible-us-east-2'

def try_match(matcher, line):
    match = matcher.regex.match(line)
    if match:
        return matcher.mk_tuple(*match.groups())

test_re()

class State:
    def __init__(self):
        self.all_infos = {}
        self.unknown_request = set()
        self.expecting_stacktrace = False


def process_line(state, line):
    state.expecting_stacktrace = False
    assign = try_match(Assign, line)
    if assign:
        state.all_infos[assign.request] = assign
    else:
        failure = try_match(Failure, line)
        if failure:
            req_info = state.all_infos.get(failure.request)
            if req_info:
                print(failure, req_info)
                state.expecting_stacktrace = True
            elif not failure.request in state.unknown_request:
                state.unknown_request.add(failure.request)
                print(failure, "unknown")

def run(state, log_reader):
    while True:
        line = log_reader.readline().decode('utf8', errors='ignore')
        if not line:
            break
        # print("DEBUG: " + line[:-1])
        if state.expecting_stacktrace and not line.startswith("20"):
            print("TB: " + line[:-1])
        else:
            process_line(state, line)

if __name__ == "__main__":
    state = State()
    with open("/var/log/nodepool/launcher.log", 'rb') as log_reader:
        run(state, log_reader)
    if state.all_infos:
        for key in ("labels", "tenant", "job"):
            counts = {}
            for info in state.all_infos.values():
                value = getattr(info, key)
                counts.setdefault(value, 0)
                counts[value] += 1
            print("== %s ==" % key)
            for (k, v) in sorted(counts.items(), key=lambda a: a[1], reverse=True):
                print("%s: %d" % (k, v))
