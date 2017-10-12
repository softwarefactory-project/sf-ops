#!/bin/bash
curl -o sf-master.qcow2 https://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2
sudo yum install -y libguestfs-tools
virt-customize -a sf-master.qcow2 --selinux-relabel \
               --run-command "yum install -y https://softwarefactory-project.io/repos/sf-release-master.rpm" \
               --run-command "yum update -y" \
               --run-command "yum install -y sf-config" \
               --run-command "mkdir /dev/shm && mount -t tmpfs shmfs /dev/shm" \
               --run-command "sfconfig --skip-setup --skip-test --skip-populate-hosts --arch /usr/share/sf-config/refarch/allinone.yaml" \
               --run-command "rm -rf /var/lib/software-factory/*"
