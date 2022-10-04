# zuul-config-update

The goal is to submit configuration change.

Given a zuul project, ZCU does:

  - edit the local zuul config
  - propose a change, using `git-review`, `git push`, `hub`


Usage:

  - ZCU replace-label cloud-fedora-33 cloud-fedora-36
