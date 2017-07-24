Backup playbook
===============

The playbook fetchs /var/lib/software-factory/backup/ from the
remote node and use bup to save incremental backup locally.

Install bup
-----------

```bash
# curl -OL https://github.com/bup/bup/archive/0.29.1.tar.gz
# tar -xvzf 0.29.1.tar.gz
# pushd bup-0.29.1
# yum install -y gcc python-devel
# ./configure && make && make install PREFIX=/usr
# popd
```

Configure the backup playbook
-----------------------------

In *groups_var/all.yaml* change the following var for:

* bup_dir: The directory where diff backup is saved. It will
  take some disk space.
* bup_save_name: The backup name. You should use the hostname of
  SF as name.
* run_sf_backup: Whether to run the sf_backup.yml playbool on the
  remote SF before fetching the backup data.
* local_backup_dir: Where to store the fetched data locally
* remote_backuped_dir: Location of the backup on the remote SF.

```yaml
local_backup_dir: "/var/lib/software-factory/backup"
remote_backuped_dir: "/var/lib/software-factory/backup/"
bup_dir: "/root/.bup"
bup_save_name: "sf-backup"
run_sf_backup: false
```

In *hosts* change the remote_backuped_host var with
the software factory host or IP.

Export the local node root user id_rsa.pub content inside software factory
/root/.ssh/authorized_keys.

Run the playbook
----------------

Note that the playbook uses /var/lib/software-factory/backup/ to store fetched
data from the remote_backuped_host. That means you can use that local
node as a spare software factory node and be able to run sfconfig --recover
at any time.

```bash
# yum install -y ansible
# ansible-playbook -i hosts -e"bup_save_name=sftests.com" backup.yml
```

After each run of the playbook you should see a new branch in
bup with the date of the run.

```bash
# bup ls sftests.com
```

Inspect the backup
------------------

To get the listing of the content in a backup you can use the ls command
of bup.

```bash
# bup ls sftests.com/latest/var/lib/software-factory/backup/gerrit/var/lib/gerrit/git/
```

Extract a backup
----------------

```bash
# bup restore sftests.com/latest/
```

You should find a var directory in your current directory. Then
you can rsync the content you need where you want.

You can also retore from a specific date for instance:

```bash
# bup restore sftests.com/2017-07-24-151720/
```
