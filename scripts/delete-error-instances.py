#!/bin/env python3

import openstack
import time
cloud = openstack.connect()
for server in cloud.compute.servers():
    if server['status'] == 'ERROR':
        try:
            print("Deleting %s" % server['id'])
            cloud.compute.delete_server(server['id'], force=True)
        except Exception as e:
            print('couldnt delete...', e)
