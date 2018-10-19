# Engineer on Duty cookbook

This document provides solutions to daily problems encountered by
engineer-on-duty. Please update each time you hit an issue
for a second time!


## PROBLEM SUMMARY

Solution including

    commands
    to --run
    to fix --the-problem


## New eng-on-duty: get ssh access to softwarefactory-project.io

You need to add your public key to `rdo-infra/rdo-infra-playbooks`.
Create a review such as

https://review.rdoproject.org/r/#/c/16901/

After merging, apply the playbook as described in

https://tree.taiga.io/project/morucci-software-factory/issue/1873


## See if all services are running

WIP SF status:
https://softwarefactory-project.io/status/

SF Zuul status:
https://softwarefactory-project.io/zuul/t/local/status

RDO Zuul status:
https://review.rdoproject.org/zuul/status

## Gerrit do not replicate on github

Gerrit service is hosted on managesf node, replication is managed by a gerrit plugin

```
$ ssh softwarefactory-project.io -l $username
$ sudo  grep -E 'Replication.*started' /var/log/gerrit/replication_log | wc -l
0
$ sudo systemctl restart gerrit
```

After few minutes, you should be able to grep data in replication_log

```
$ sudo  grep -E 'Replication.*started' /var/log/gerrit/replication_log
[2018-10-19 18:24:33,249] [59e6fa0c] Replication to git@github.com:redhat-cip/dci-feeder-rhel.git started...
...
```
