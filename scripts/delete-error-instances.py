#!/bin/env python3

import shade
import time
cloud = shade.openstack_cloud()
servers = cloud.list_servers()
print("%d servers" % len(servers))

# TODO: clean fip, ports, volumes, ...

for server in filter(lambda x: x['status'] == 'ERROR', servers):
  print("Deleting %s" % server['id'])
  try:
      if not cloud.delete_server(server['id']):
          print("delete failed")
  except Exception as e:
      print('couldnt delete...', e)
  time.sleep(0.5)

servers = cloud.list_servers()
print("%d servers remaining" % len(servers))
