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

In groups_var/all.yaml changes the remote_backuped_host var with
the software factory host or IP.

```yaml
local_backup_dir: "/var/lib/software-factory/backup"
remote_backuped_dir: "/var/lib/software-factory/backup/"
remote_backuped_host: "38.145.32.196"
remote_user: "root"
bup_dir: "/root/.bup"
```

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
# ansible-playbook backup.yml
```

After each run of the playbook you should see a new branch in
bup with the date of the run.

```bash
# bup ls sf-backup
```

Extract a backup
----------------

```bash
# bup restore sf-backup/latest/
```

You should find a var directory in your current directory. Then
you can rsync the content you need where you want.

You can also retore from a specific date for instance:

```bash
# bup restore sf-backup/2017-07-24-151720/
```
