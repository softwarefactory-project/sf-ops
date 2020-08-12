let Ansible =
      https://raw.githubusercontent.com/softwarefactory-project/dhall-ansible/b457f27b52c92bc7bd2787eedf2b66f318e1f5d1/package.dhall sha256:6081f2916f7d8a07f5852cbea50727a6a04426c1bcc7b88867d306db9cb4f486

in  \(sf-version : Text) ->
    \(install-server-name : Text) ->
      [ Ansible.Play::{
        , hosts = install-server-name
        , gather_facts = Some False
        , tasks = Some
          [ Ansible.Task::{
            , name = Some "Check tmp repos"
            , command = Some "grep -r buildset /etc/yum.repos.d"
            , register = Some "_tmp_repos"
            , failed_when = Some "_tmp_repos.stdout != \"\""
            }
          , Ansible.Task::{
            , name = Some "Clean the config clone"
            , become = Some True
            , shell = Some Ansible.Shell::{
              , cmd =
                  ''
                  #!/bin/sh -e -x
                  rm -Rf /var/lib/software-factory/git/*.patch
                  cd /root/config
                  git fetch origin
                  git clean -x -f -d
                  git reset --hard origin/master
                  ''
              }
            }
          , Ansible.Task::{
            , name = Some "Install ${sf-version} release"
            , package = Some Ansible.Package::{
              , name =
                  "https://softwarefactory-project.io/repos/sf-release-${sf-version}.rpm"
              , state = "present"
              }
            , become = Some True
            }
          , Ansible.Task::{
            , name = Some "Update sf-config"
            , package = Some Ansible.Package::{
              , name = "sf-config"
              , state = "latest"
              }
            , become = Some True
            }
          , Ansible.Task::{
            , name = Some "Run sf-config"
            , command = Some "sfconfig --update"
            , become = Some True
            }
          ]
        }
      ]
