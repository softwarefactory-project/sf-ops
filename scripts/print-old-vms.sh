#!/bin/bash

# Script is iterating on each server available in the OS_CLOUD project.
# If server is older than eg. 12 hours, it will print a message.

DAY_AGO=$(date -d "$(date '+%Y-%m-%dT%H:%M:%S' -d '12 hour ago')" +%s)
OLD_SERVERS=0

if [ -z "$OS_CLOUD" ]; then
    echo "Can not continue. Please export OS_CLOUD first!"
    exit 1
fi

for server in $(openstack server list | awk '{print $2}' | awk 'FNR>3'); do
    # NOTE: we should watch on created_at not updated_at, due the state can be
    # reset or changed to deleting by nodepool, but if the instance is running
    # over 12 hours, it probably should be deleted.
    SERVER_INFO=$(openstack server show "$server" -c OS-EXT-STS:task_state -c created_at -c name -f shell)
    SERVER_DATE=$(echo "$SERVER_INFO" | grep 'created_at' | cut -f2 -d'=' | sed 's/\"//g')
    SERVER_NAME=$(echo "$SERVER_INFO" | grep 'name' | cut -f2 -d'=' | sed 's/\"//g')
    SERVER_STATE=$(echo "$SERVER_INFO" | grep 'os_ext_sts_task_state' | cut -f2 -d'=' | sed 's/\"//g' )
    EPOCH_DATE=$(date -d "$SERVER_DATE" +%s)
    if [ "$DAY_AGO" -gt "$EPOCH_DATE" ]; then
        echo "WARNING: Server $server - $SERVER_NAME - is old - $SERVER_DATE and got state: $SERVER_STATE"
        OLD_SERVERS=$((OLD_SERVERS+1))
    else
        echo "INFO: Server $server - $SERVER_NAME was created in last 12 hours - $SERVER_DATE"
    fi
done

echo "There are $OLD_SERVERS servers, that was created 12 hours ago."
