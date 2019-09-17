#!/bin/python3
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
The goal of script is to convert scl/*/*.spec to rpms/

* convert spec files
* generated ordered script to build
* validate convertion works
"""

from pathlib import Path
from subprocess import Popen
from typing import Dict, List, Set
import yaml

GIT = Path("~/git").expanduser()
RPMS = Path("~/git/rpms").expanduser()


def execute(args: List[str], cwd: Path) -> None:
    if Popen(args, cwd=str(cwd)).wait():
        raise RuntimeError(f"{args}: failed")


def cloneRepo(path: str) -> Path:
    dest = (GIT / path)
    if (dest / ".git").is_dir():
        return GIT / path
    url = "https://softwarefactory-project.io/r/" + path
    dest.mkdir(exist_ok=True, parents=True)
    execute(["git", "clone", "--depth", "1", url, str(dest)], cwd=GIT)
    return dest


config = cloneRepo("config")


def getSclList(config: Path) -> List[str]:
    sclFile = config / "resources" / "scl.yaml"
    scls = yaml.load(sclFile.read_text())
    return list(scls['resources']['repos'].keys())


def getSpecFileContent(repo: Path) -> List[str]:
    return (repo / (repo.name.replace("-distgit", "") + ".spec")).read_text().split('\n')


if "sclList" not in locals():
    sclList = getSclList(config)
    for ignore in ("scl/cauth-distgit",
                   "scl/python-adal-distgit",
                   "scl/enable-py3-distgit",
                   "scl/python-setuptools",
                   "scl/python-shade-distgit",
                   "scl/scipy-distgit",
                   "scl/Cython-distgit"):
        if ignore in sclList:
            sclList.remove(ignore)

if "sclSpecs" not in locals():
    sclSpecs: Dict[str, List[str]] = {}

if len(sclSpecs) != len(sclList):
    for scl in sclList:
        sclPath = cloneRepo(scl)
        if scl not in sclSpecs:
            sclSpecs[scl] = getSpecFileContent(sclPath)


def sclReplace(line: str) -> str:
    if line.lower().startswith("source") or \
       line.lower().startswith("patch") or \
       line.lower().startswith("%autosetup") or \
       line.lower().startswith("%setup") or \
       line.startswith("mv python-base"):
        return line
    for k, v in (
            ("%{?scl_prefix}python", "python3"),
            ("%{?scl_prefix}", ""),
            ("2to3 ", "2to3-3 "),
            (" PyYAML", " python3-pyyaml"),
            (" numpy", " python3-numpy"),
            (" scipy", " python3-scipy"),
            # python-selinux hardcode that...
            ("/python3.5/", "/python3.6/"),
            (" GitPython", " python3-GitPython"),
            (" python-", " python3-"),
            ("%{python_sitelib}", "%{python3_sitelib}"),
            ("%{?scl:%_root_libdir}%{?!scl:%_libdir}", "%{_libdir}"),
            ("%{?scl:%_root_includedir}%{?!scl:%_includedir}",
             "%{_includedir}")
    ):
        line = line.replace(k, v)
    return line


def sclIgnore(line: str) -> bool:
    return not (
        line.startswith("%{?scl:%scl") or
        line.startswith("%{?scl:scl") or
        line.startswith("%{?scl:EOF") or
        line.startswith("%{!?scl:%global") or
        "scl-utils" in line or
        "enable-py3" in line or
        "jinja2/async" in line or
        line == '%{?scl:"}'
    )


def convertSclToSpec(spec: List[str]) -> List[str]:
    name: str = ""
    result: List[str] = []
    # Look for name
    for line in spec:
        if line.lower().startswith("name:"):
            name = line.split()[1]
            result.append(
                "%global pkg_name " + line.split(
                    "python-" if "python-" in line else
                    "%{?scl_prefix}"
                    )[-1])
            break
    else:
        raise RuntimeError("Couldn't find name")

    # Look for bindir when package name starts with 'python-'
    inject_rename: bool = False
    if "python-" in name:
        for line in spec:
            if line.startswith("%{_bindir}"):
                inject_rename = True

    in_install: bool = False
    for line in map(sclReplace, filter(sclIgnore, spec)):
        if inject_rename:
            if in_install and (
               line.startswith("%check") or line.startswith("%file") \
               or line.startswith("%pre")):
                # End of %install block, thus inject rename snip
                result.append("""for bin in %{buildroot}%{_bindir}/*; do
  mv ${bin} ${bin}-%{python3_version}
  ln -s $(basename ${bin})-%{python3_version} ${bin}-3
done""")
                in_install = False
            elif line.startswith("%install"):
                in_install = True
        if inject_rename and line.startswith("%{_bindir}/"):
            if not line.endswith("*"):
                line += "*"

        if line.startswith("%{?scl:Requires"):
            result.append("Requires:       python3")
            result.append(
                "%{?python_provide:%python_provide "
                "python3-%{pkg_name}}")
        elif line.startswith("%{?scl:BuildRequires"):
            result.append("BuildRequires:  python3-devel")
        else:
            result.append(line)
    return result


def pathToPkgName(scl: str) -> str:
    return scl.replace("scl/", "").replace("-distgit", "")


def updateFile(path: Path, content: str) -> bool:
    if (path.exists() and path.read_text() != content) or (
            not path.exists()):
        path.write_text(content)
        return True
    return False


newSpecs: Dict[str, List[str]] = {}

# Generate new spec files in newSpects collection
for scl in sclList:
    sclName = pathToPkgName(scl)
    rpms = RPMS / sclName
    rpms.mkdir(parents=True, exist_ok=True)
    specFile = (rpms / (sclName + ".spec"))
    newSpecs[scl] = convertSclToSpec(sclSpecs[scl])
    if updateFile(specFile, "\n".join(newSpecs[scl])):
        print("Generated", specFile)

pkgReqs: Dict[str, Set[str]] = {}


# Collect requirements to look for the best build order
def isReq(line: str) -> bool:
    return line.lower().startswith("requires:") or \
        line.lower().startswith("buildrequires:")


for scl in sclList:
    pkgReqs[scl] = set()
    for line in filter(isReq, newSpecs[scl]):
        pkgReqs[scl].add(line.split()[1])


script: List[str] = ["#!/bin/bash", "set -ex"]

sclOrder = list(dict(
    sorted(pkgReqs.items(), key=lambda x: len(x[1]))).keys())

for delay in (

        "rdopkg",

        # "python-pyopenssl",
        # "python-jwcrypto",

        "python-github3",

        #"python-dulwich",
        #"python-reno",
        #"python-oslo-context",
        #"python-oslo-policy",
        "python-XStatic-DataTables",
        "python-scikit-learn",

        # "python-keystoneauth1",
        #"python-oslo-serialization",
        #"python-keystoneclient",
        #"python-glanceclient",
        #"python-oslo-log",
        #"python-os-client-config",
        #"python-osc-lib",
        "python-openstackclient",


        #"python-jinja2",
        "python-flask-sqlalchemy",
        "python-XStatic-jQuery",
        "python-portend",
        "python-flask",
        "python-flask-frozen",
        "python-flask-script",
        "python-flask-httpauth",
        "python-flask-migrate",
        "python-sphinxcontrib-programoutput",
        "zuul-jobs",
        "nodepool",
        "python-jeepney"):
    n = "scl/" + delay + "-distgit"
    sclOrder.remove(n)
    sclOrder.append(n)


for scl in sclOrder:
    name = pathToPkgName(scl)
    rpms = RPMS / name
    if (rpms / ".built").exists():
        continue
    script.append("echo Building %s" % (rpms))
    #script.append("spectool -g -S -C",
    #         scl, str(rpms / (name + ".spec"))], cwd=GIT)


    script.append(
        (
            "rpmbuild "
            "--define '_sourcedir {src_dir}' "
            "--define '_topdir {dest_dir}' "
            "-bs {spec_file}"
        ).format(
            src_dir=(GIT / scl),
            dest_dir=(rpms),
            spec_file=(rpms / (name + ".spec"))
        )
    )
    script.append(
        (
            "yum-builddep -y {dest_dir}/SRPMS/*.src.rpm"
        ).format(
            dest_dir=(rpms)
        )
    )
    script.append(
        (
            "rpmbuild "
            "--define '_sourcedir {src_dir}' "
            "--define '_topdir {dest_dir}' "
            "-bb {spec_file}"
        ).format(
            src_dir=(GIT / scl),
            dest_dir=(rpms),
            spec_file=(rpms / (name + ".spec"))
        )
    )
    script.append(
        (
            "yum install -y $(find {dest_dir}/RPMS/ -name '*.rpm') || :"
        ).format(dest_dir=rpms)
    )
    script.append(
        ("touch {dest_dir}/.built").format(dest_dir=rpms)
    )

(GIT / "build.sh").write_text("\n".join(script))

print("Done")
