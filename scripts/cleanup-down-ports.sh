#!/bin/bash

DAY_AGO=$(date -d "$(date '+%Y-%m-%dT%H:%M:%S' -d '1 day ago')" +%s)
for port in $(openstack port list | grep -i down | awk '{print $2}'); do
    PORT_DATE=$(date -d "$(openstack port show -c updated_at -f value $port)" +%s);
    echo "Port date $port is $(date -d@$PORT_DATE) ($OS_CLOUD)"
    if [ "$DAY_AGO" -gt "$PORT_DATE" ]; then
        echo "Deleting port $port"
        openstack port delete $port;
    fi;
done
