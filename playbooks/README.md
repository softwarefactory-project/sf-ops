# Instructions how to run playbook add_image_to_glance.yaml

* Run the playbook from From the Software Factory install-server node.
* Playbook is located in /root/sf-ops/playbooks (sudo su -; cd sf-ops/)
* Use the `--extra-vars "image_url=<URL> cloud=<cloud>"` option to pass the image URL and the destination cloud to the ansible-playbook.
Example:
`ansible-playbook --extra-vars "image_url=http://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud-1809.raw.tar.gz cloud=rdo-cloud" add_image_to_glance.yaml`
