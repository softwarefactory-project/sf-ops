Koji backup playbook
====================

The playbook:

- prepares the bup database
- registers the koji node in the inventory
- dumps the koji postgresql database
- fetchs the koji db dump locally
- rsyncs /mnt/koji that contain all RPMs repos locally
- runs incremental backup
- rsyncs defined sf-relases to /var/www/html/sf/

See ../../backup/ansible/README.md for more details about bup usage if you
need to recover or chekc something.

Note that the BUP_DIR is BUP_DIR=/var/lib/backup/bup-koji/<year-month>

Run the backup periodically
---------------------------

Insert in the root crontab with *crontab -e* the following statement:

```bash
0 1 * * * ansible-playbook /root/sf-ops/backup-koji/ansible/backup.yml
```
