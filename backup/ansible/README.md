Backup playbook
===============

The playbook fetchs /var/lib/software-factory/backup/ from the
remote node (Software Factory) and uses bup to save incremental backup locally.

Install bup
-----------

```bash
curl -OL https://github.com/bup/bup/archive/0.29.1.tar.gz
tar -xvzf 0.29.1.tar.gz
pushd bup-0.29.1
sudo yum install -y gcc python-devel
./configure && make && sudo make install PREFIX=/usr
popd
```

Configure the backup playbook
-----------------------------

In *groups_var/all.yaml* change the following var for:

* bup_dir: The base directory where the incremental backup is saved.
  A bup directory named *year-month* is created under bup_dir.
* run_sf_backup: Whether to run the sf_backup.yml playbool on the
  remote SF before fetching the backup data.
* local_dir: Where to store the fetched data locally
* remote_dir: Location of the backup on the remote SF.
* sf_host: The hostname or IP of the remote SF.
* sf_hosts: The hostnames or IP adresses of the remote host (required when
            not all desired services are on the same host).

```yaml
sf_host: "sftests.com"
sf_hosts:
local_dir: "/var/lib/backup/{{ sf_host }}/"
remote_dir: "/var/lib/software-factory/backup/"
bup_dir: "/var/lib/backup/bup/"
run_sf_backup: true
```

Export the local node root user id_rsa.pub content inside Software Factory
/root/.ssh/authorized_keys.

Run the playbook
----------------

Every month the BUP_DIR is a new directory. That means a full backup
is done every month then incremental backup is performed during the
the current month. This is recommended by the BUP manual as support for
pruning old backups is currently experimental.

```bash
sudo yum install -y ansible
sudo ansible-playbook -e"sf_host=sftests.com" backup.yml
```

After each run of the playbook you should see a new branch in
bup with the date of the run.

```bash
sudo BUP_DIR=/var/lib/backup/bup/<year-month> bup ls sftests.com
```

Inspect the backup
------------------

To get the listing of the content in a backup you can use the ls command
of bup.

```bash
sudo BUP_DIR=/var/lib/backup/bup/<year-month> bup ls sftests.com/latest/var/lib/software-factory/backup/gerrit/var/lib/gerrit/git/
```

Extract a backup
----------------

```bash
sudo BUP_DIR=/var/lib/backup/bup/<year-month> bup restore sftests.com/latest/
```

You should find a var directory in your current directory. Then
you can rsync the content you need where you want.

You can also retore from a specific date for instance:

```bash
sudo BUP_DIR=/var/lib/backup/bup/<year-month> bup restore sftests.com/2017-07-24-151720/
```

Run the backup periodically
---------------------------

Insert in the root crontab with *crontab -e* the following statement:

```bash
0 5 * * * ansible-playbook -e sf_host=softwarefactory-project.io /root/sf-ops/backup/ansible/backup.yml
```

Clean old backups
-----------------

Previous backups can be removed from the filesystem by deleting
old backup directories */var/lib/backup/bup/<year-month>*.
