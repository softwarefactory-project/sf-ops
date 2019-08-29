#!/bin/env python3
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

import copy
import requests
from subprocess import Popen
from typing import Any, Dict, List, Set, NewType, TypeVar, Tuple, Iterator
from pathlib import Path
from textwrap import dedent

# Optional[T] = Union[None, T]

zuul_api: str = "https://softwarefactory-project.io/zuul/api/"

# Types, miam
# Basic types
LabelName = NewType('LabelName', str)
JobName = NewType('JobName', str)
ProjectName = NewType('ProjectName', str)
TenantName = NewType('TenantName', str)
TenantConfig = Dict[str, Any]
JobConfig = Dict[str, Any]
ProjectConfig = Dict[str, Any]
JobConfigs = List[JobConfig]
# Complex types
ConfigStore = Dict[TenantName, TenantConfig]


def loadConfigs(zuul_api: str) -> ConfigStore:
    configs: ConfigStore = {}
    for tenant in requests.get(zuul_api + "tenants").json():
        tenant_config_url: str = (
            zuul_api + "tenant/" + tenant["name"] + "/config")
        print("Fetching", tenant_config_url)
        configs[
            tenant["name"]] = requests.get(tenant_config_url).json()
    return configs


if "configs" not in locals():
    configs: ConfigStore = loadConfigs(zuul_api)


def loadLabels(zuul_api: str) -> Set[LabelName]:
    labels: Set[LabelName] = set()
    for label in requests.get(
            zuul_api + "tenant/local/labels").json():
        labels.add(label['name'])
    return labels


if "labels" not in locals():
    labels: Set[LabelName] = loadLabels(zuul_api)


SourceContext = Dict[str, str]
glLabelContext: Dict[LabelName, List[SourceContext]] = {}
JobKey = NewType('JobKey', str)
glJobProject: Dict[JobKey, Set[ProjectName]] = {}


def makeJobKey(tenant: TenantName, job: JobName) -> JobKey:
    return JobKey(f"{tenant}:{job}")


def recordJobProject(
        tenant: TenantName,
        job: JobName,
        project: ProjectName) -> None:
    job_key = makeJobKey(tenant, job)
    glJobProject.setdefault(job_key, set())
    glJobProject[job_key].add(project)


JobsLabels = Dict[JobName, Set[LabelName]]
TenantJobsLabels = Dict[JobKey, Set[LabelName]]


def walkTenant(tenant: TenantConfig) -> JobsLabels:
    # Populate the glLabelContext dict

    jobsLabels: JobsLabels = {}
    # Index job for easier access
    jobsMap: Dict[JobName, JobConfigs] = {}
    for job in tenant["layout"]["jobs"]:
        jobsMap[job[0]["name"]] = job

    def nodesetToLabels(nodeset: Any) -> Set[LabelName]:
        return set([node["label"] for node in nodeset["nodes"]]) \
                   if nodeset else set()

    def findJobNodes(
            job: JobName, fromProject: ProjectName) -> Set[LabelName]:
        if job in jobsLabels:
            return jobsLabels[job]
        jobsLabels[job] = set()

        for jobObj in jobsMap[job]:
            if "nodeset" in jobObj:
                jobLabels = nodesetToLabels(jobObj["nodeset"])
                recordJobProject(tenant["name"], job, fromProject)
                jobsLabels[job].update(jobLabels)
                for label in jobLabels:
                    glLabelContext.setdefault(label, [])
                    ctx = copy.copy(jobObj["source_context"])
                    ctx["tenant"] = tenant["name"]
                    glLabelContext[label].append(ctx)

            if "parent" in jobObj and jobObj["parent"]:
                findJobNodes(jobObj["parent"], fromProject)
                recordJobProject(tenant["name"], job, fromProject)
                jobsLabels[job].update(jobsLabels[jobObj["parent"]])
        return jobsLabels[job]

    def walkProject(project: ProjectConfig) -> None:
        for config in project["configs"]:
            for pipeline in config["pipelines"]:
                for jobs in pipeline["jobs"]:
                    for job in jobs:
                        recordJobProject(
                            tenant["name"], job["name"],
                            project["name"])
                        findJobNodes(job["name"], project["name"])

    for project in tenant["projects"]:
        walkProject(project)
    return jobsLabels


def prefixJobsNameWithTenant(
        tenant: TenantName,
        jobsLabels: JobsLabels) -> TenantJobsLabels:

    return dict(map(lambda x: (makeJobKey(tenant, x[0]), x[1]),
                    jobsLabels.items()))


LabelsJobs = Dict[LabelName, Set[JobName]]
LabelsTenantJobs = Dict[LabelName, Set[JobKey]]

# Is this a generic?
S = TypeVar('S', JobKey, JobName)
Labels = Set[LabelName]


def inverseDict(
        jobsLabels: Dict[S, Labels]) -> Dict[LabelName, Set[S]]:
    labelsJobs: Dict[LabelName, Set[S]] = {}
    for job, labels in jobsLabels.items():
        for label in labels:
            labelsJobs.setdefault(label, set())
            labelsJobs[label].add(job)
    return labelsJobs


def globalJobsNodes(configs: ConfigStore) -> LabelsTenantJobs:
    globalLabelsJobs: LabelsTenantJobs = {}
    for tenant, tenantConfig in configs.items():
        tenantJobsLabels = prefixJobsNameWithTenant(
            tenant, walkTenant(tenantConfig))
        for label, jobs in inverseDict(tenantJobsLabels).items():
            globalLabelsJobs.setdefault(label, set())
            globalLabelsJobs[label].update(jobs)
    return globalLabelsJobs


def makeGerritId(label: LabelName, project: Path) -> str:
    from hashlib import sha1
    return "Change-Id: I%s" % sha1(b" ".join(
        map(lambda x: x.encode('utf-8'),
            (label, str(project))))).hexdigest()


glLabelsJobs: LabelsTenantJobs = globalJobsNodes(configs)

labelsReplace: Dict[LabelName, LabelName] = dict(map(
    lambda x: (LabelName(x[0]), LabelName(x[1])), (
        ("f27-oci", "runc-fedora"),
        ("runc-centos-7", "runc-centos"),
        ("dib-fedora-28", "cloud-fedora-30"),
        ("rdo-fedora-stable", "cloud-fedora-30"),
        ("cloud-fedora-29", "cloud-fedora-30"),
        ("dib-dci-centos-7", "cloud-centos-7"),
        ("dib-centos-7", "cloud-centos-7"),
        ("rdo-fedora-28", "cloud-fedora-30"),
    )))


LabelIterator = Iterator[Tuple[LabelName, Set[JobKey]]]


def getLabelJobs(labelsTenantJobs: LabelsTenantJobs) -> LabelIterator:
    return reversed(sorted(labelsTenantJobs.items(),
                           key=lambda x: len(x[1])))


def printLabelUsage(labelsTenantJobs: LabelsTenantJobs) -> None:
    for label, jobs in getLabelJobs(labelsTenantJobs):
        print(label, "used by", len(jobs))


def getConnection(tenant: TenantName) -> str:
    if tenant == "local":
        return "https://softwarefactory-project.io/r"
    elif tenant == "rdoproject.org":
        return "https://review.rdoproject.org/r"
    elif tenant == "ansible":
        return "https://github.com"
    else:
        return "TBD"


def execute(args: List[str], cwd: Path) -> None:
    if Popen(args, cwd=str(cwd)).wait():
        raise RuntimeError("%s: failed" % " ".join(args))


ProjectDir = Path
ZuulFile = Path


def fixLabelUsage(
        label: LabelName, newLabel: LabelName,
        jobs: Set[JobKey]) -> None:
    zuul_paths: Set[Tuple[ProjectDir, ZuulFile]] = set()
    for ctx in glLabelContext[label]:
        url = getConnection(TenantName(ctx["tenant"]))
        project_dir = Path(ctx["tenant"]) / ctx["project"]
        project_url = url + "/" + ctx["project"]
        if not (project_dir / ".git").exists():
            print("Need to clone", project_url, "to", project_dir)
            project_dir.mkdir(parents=True, exist_ok=True)
            execute(["git", "clone", project_url, str(project_dir)],
                    Path("."))
        zuul_path = project_dir / ctx["path"]
        zuul_paths.add((project_dir, zuul_path))

    for project_dir, zuul_path in zuul_paths:
        execute(["git", "reset", "--hard", "origin/master"],
                project_dir)
        orig_file = zuul_path.read_text()
        new_file = orig_file.replace(label, newLabel)
        if orig_file != new_file:
            zuul_path.write_text(new_file)
            print(f"{zuul_path}: updated!")
        job_list = "\n        - ".join(map(
            lambda x: x.split(':')[1] + " used by: %s" % (
                ", ".join(glJobProject[x])
            ), sorted(jobs)))
        gerrit_cookie = makeGerritId(label, project_dir)
        commit_message = dedent(f"""
        Automatic replacement of label {label} by {newLabel}

        {label} is being replaced by {newLabel}.
        The following jobs need to be rechecked:
        - {job_list}

        {gerrit_cookie}
        """)[1:]

        print("==== Commit in", zuul_path)
        print(commit_message)
        execute(["git", "commit", "-a", "-m", commit_message],
                project_dir)
#       execute(["git", "review"], project_dir)


def fixLabelsUsage(labelsTenantJobs: LabelsTenantJobs,
                   min_usage: int = 10) -> None:
    for label, jobs in getLabelJobs(glLabelsJobs):
        if len(jobs) > min_usage or label not in labelsReplace:
            continue
        print(f"Trying to replace {label} by {labelsReplace[label]}")
        try:
            fixLabelUsage(label, labelsReplace[label], jobs)
        except Exception as e:
            print("Oops", e)


fixLabelsUsage(glLabelsJobs)
