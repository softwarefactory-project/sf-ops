# Instructions how to run playbook add_image_to_glance.yaml

Use the `--extra-vars "image_url=<URL> ` option to pass the image URL to ansible-playbook. 
Example:
`ansible-playbook --extra-vars "image_url=http://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud-1809.raw.tar.gz" sf-add_image_to_glance.yaml`
