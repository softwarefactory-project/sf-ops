#!/bin/bash

skipped_counter=0
deleted_counter=0

DAY_AGO=$(date -d "$(date '+%Y-%m-%dT%H:%M:%S' -d '1 day ago')" +%s)
for port in $(openstack port list | grep -i down | awk '{print $2}'); do
    PORT_DATE=$(date -d "$(openstack port show -c updated_at -f value $port)" +%s);
    echo "Port date $port is $(date -d@$PORT_DATE) ($OS_CLOUD)"
    if [ "$DAY_AGO" -gt "$PORT_DATE" ]; then
        echo "Deleting port $port"
        openstack port delete $port;
        deleted_counter=$((deleted_counder+1))
    else
        skipped_counter=$((skipped_counter+1))
    fi;
done

echo "The script have deleted: ${deleted_counter} and skip: ${skipped_counter} ports"
