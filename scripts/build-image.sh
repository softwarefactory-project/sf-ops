#!/bin/bash

imagename=${IMAGENAME:-sf-master.qcow2}
release=${RELEASE:-master}

curl -o $imagename https://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2
sudo yum install -y libguestfs-tools
virt-customize -a $imagename --selinux-relabel \
               --run-command "yum install -y https://softwarefactory-project.io/repos/sf-release-${release}.rpm" \
               --run-command "yum update -y" \
               --run-command "yum install -y sf-config" \
               --run-command "mkdir /dev/shm && mount -t tmpfs shmfs /dev/shm" \
               --run-command "sfconfig --skip-setup --skip-test --skip-populate-hosts --arch /usr/share/sf-config/refarch/allinone.yaml" \
               --run-command "rm -rf /var/lib/software-factory/*"
