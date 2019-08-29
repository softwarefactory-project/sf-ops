#!/bin/env python
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

zuul_api = "https://softwarefactory-project.io/zuul/api/"
# Dict[tenant_name, tenant_config]
# configs = {}
# List[label_name]
# labels = []


def loadConfigs(zuul_api):
    configs = {}
    for tenant in requests.get(zuul_api + "tenants").json():
        tenant_config_url = (
            zuul_api + "tenant/" + tenant["name"] + "/config")
        print("Fetching", tenant_config_url)
        configs[
            tenant["name"]] = requests.get(tenant_config_url).json()
    return configs

if not configs:
    configs = loadConfigs(zuul_api)

def loadLabels(zuul_api):
    labels = {}
    for label in requests.get(zuul_api + "tenant/local/labels").json():
        labels[label['name']] = []
    return labels

if not labels:
    labels = loadLabels(zuul_api)

glLabelContext = {}
glJobProject = {}


def recordJobProject(tenant_name, job_name, project_name):
    job_key = tenant_name + ":" + job_name
    glJobProject.setdefault(job_key, set())
    glJobProject[job_key].add(project_name)


def walkTenant(tenant):
    # Populate the glLabelContext dict and
    #   return the Dict[job_name, label_list]
    jobsNodes = {None: []}
    # Index job for easier access
    jobsMap = {}
    for job in tenant["layout"]["jobs"]:
        jobsMap[job[0]["name"]] = job

    def nodesetToLabels(nodeset):
        return [node["label"] for node in nodeset["nodes"]] \
            if nodeset else []

    def findJobNodes(job, fromProject):
        if job in jobsNodes:
            return jobsNodes[job]
        jobsNodes[job] = []

        for jobObj in jobsMap[job]:
            if "nodeset" in jobObj:
                jobLabels = nodesetToLabels(jobObj["nodeset"])
                recordJobProject(tenant["name"], job, fromProject)
                jobsNodes[job].extend(jobLabels)
                for label in jobLabels:
                    glLabelContext.setdefault(label, [])
                    ctx = copy.copy(jobObj["source_context"])
                    ctx["tenant"] = tenant["name"]
                    glLabelContext[label].append(ctx)

            if "parent" in jobObj:
                findJobNodes(jobObj["parent"], fromProject)
                recordJobProject(tenant["name"], job, fromProject)
                jobsNodes[job].extend(jobsNodes[jobObj["parent"]])
        return jobsNodes[job]

    def walkProject(project):
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
    return jobsNodes

def prefixJobsNameWithTenant(tenantName, jobsNodes):
    return dict(map(
        lambda x: (tenantName + ":" + (x[0] if x[0] else "None"),
                   x[1]), jobsNodes.items()))

def jobsNodesToLabelsJobs(jobsNodes):
    labelsJobs = {}
    for job, labels in jobsNodes.items():
        for label in labels:
            labelsJobs.setdefault(label, set())
            labelsJobs[label].add(job)
    return labelsJobs

def globalJobsNodes(configs):
    globalLabelsJobs = {}
    for tenant, tenantConfig in configs.items():
        jobsNodes = prefixJobsNameWithTenant(
            tenant, walkTenant(tenantConfig))
        for label, jobs in jobsNodesToLabelsJobs(jobsNodes).items():
            globalLabelsJobs.setdefault(label, set())
            globalLabelsJobs[label].update(jobs)
    return globalLabelsJobs

def makeGerritId(label, project_dir):
    from hashlib import sha1
    return "Change-Id: I%s" % sha1(" ".join(
        (label, project_dir))).hexdigest()

glLabelsJobs = globalJobsNodes(configs)

labelsReplace = {
    "f27-oci": "runc-fedora",
    "runc-centos-7": "runc-centos",
    "dib-fedora-28": "cloud-fedora-30",
    "rdo-fedora-stable": "cloud-fedora-30",
    "cloud-fedora-29": "cloud-fedora-30",
    "dib-dci-centos-7": "cloud-centos-7",
    "dib-centos-7": "cloud-centos-7",
    "rdo-fedora-28": "cloud-fedora-30",
}

for label, jobs in reversed(sorted(glLabelsJobs.items(),
                                   key=lambda x: len(x[1]))):
    if (len(jobs)) <= 10:
        print label, "used by", len(jobs)

        if label not in labelsReplace:
            continue
        print "Defined in:"
        zuul_paths = set()
        for ctx in glLabelContext[label]:
            if ctx["tenant"] == "local":
                url = "https://softwarefactory-project.io/r"
            elif ctx["tenant"] == "rdoproject.org":
                url = "https://review.rdoproject.org/r"
            elif ctx["tenant"] == "ansible":
                url = "https://github.com"
            else:
                url = "TBD"

            project_dir = ctx["tenant"] + "/" + ctx["project"]
            project_url = url + "/" + ctx["project"]
            if not os.path.exists(project_dir + "/.git"):
                os.makedirs(project_dir)
                print "Cloning %s to %s" % (project_url, project_dir)
                if subprocess.Popen(
                    ["git", "clone", project_url, project_dir]
                ).wait():
                    print "Couldn't clone", project_url
            zuul_path = "%s/%s" % (project_dir, ctx["path"])
            zuul_paths.add((project_dir, zuul_path))

        for project_dir, zuul_path in zuul_paths:
            if subprocess.Popen([
                    "git", "reset", "--hard", "origin/master"],
                                cwd=project_dir).wait():
                print "Couldn't reset", project_dir
                continue
            orig_file = open(zuul_path).read()
            new_file = orig_file.replace(
                label, labelsReplace[label]
            )
            if orig_file != new_file:
                with open(zuul_path, "w") as of:
                    of.write(new_file)
                    print zuul_path + ": updated!"
            commit_message = """Automatic replacement of label {old_label} by {new_label}

{old_label} is being replaced by {new_label}. The following jobs need to be rechecked:
- {job_list}

{gerrit_cookie}
""".format(
    old_label=label, new_label=labelsReplace[label],
    job_list="\n- ".join(map(lambda x: x.split(':')[1] + " used by: %s" % (
        ", ".join(glJobProject[x])
    ), sorted(jobs))),
    gerrit_cookie=makeGerritId(label, project_dir)
)
            print "==== Commit in", zuul_path
            subprocess.Popen(
                ["git", "commit", "-a", "-m", commit_message],
                cwd=project_dir).wait()
            subprocess.Popen(
                ["git", "review"], cwd=project_dir).wait()
