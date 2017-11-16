Operation scripts
======================

build-image.sh
----------------

This scripts is used to build an SF image using the last centos-cloud.
It will install sf-release-X.X.rpm and run a sfconfig (only install
tasks) based on the allinone architecture.

Without the environment variables the master version of
Software Factory will be provisionned on the image.

$ IMAGENAME=sf-2.7.qcow2 RELEASE=2.7 ./build-image.sh
