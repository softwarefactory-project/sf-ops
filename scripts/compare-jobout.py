#!/bin/env python3
# Copyright 2020, Red Hat
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

import functools
import json
import datetime
from typing import Any, List, NewType, Tuple


# A duration in second
Duration = NewType("Duration", int)
def calc_duration(start : str, end: str) -> Duration:
    def mk_time(time: str) -> datetime.datetime:
        return datetime.datetime.fromisoformat(time.split('.')[0])
    return Duration(int((mk_time(end) - mk_time(start)).total_seconds()))


def calc_play_duration(play: Any) -> Duration:
    return calc_duration(play["duration"]["start"], play["duration"]["end"]) \
        if play["duration"].get("end") is not None else Duration(0)


def play_time(jobout: Any) -> List[Tuple[str, int]]:
    return [
        (job["playbook"],
         functools.reduce(
             lambda x, y: x + y,
             [calc_play_duration(play["play"])
              for play in job["plays"]],
             0)
        )
        for job in jobout
    ]


def play_times(jobouts: List[Tuple[str, Any]]) -> List[str]:
    plays = list(map(lambda jobout: play_time(jobout[1]), jobouts))
    results = []
    for idx in range(len(plays[0])):
        if plays[0][idx][1] == 0:
            continue
        if plays[0][idx][0] != plays[1][idx][0]:
            return ["error: different play order: %s" % str(plays)]
        tdiff = plays[0][idx][1] - plays[1][idx][1]
        winner = 1 if tdiff < 0 else 0
        name = jobouts[winner][0]
        pdiff = (tdiff * 100) / plays[winner][idx][1]
        results.append(
            "{:<80s}: {:<10s}{:5d} sec ({:06.02f} %)".format(plays[0][idx][0], name, tdiff, pdiff))
    return results


if __name__ == "__main__":
    import argparse
    import requests
    import os.path
    parser = argparse.ArgumentParser()
    for x in range(2):
        parser.add_argument("log_url_job" + str(x))
        parser.add_argument("provider" + str(x))
    args = parser.parse_args()

    def get_log(url: str) -> Any:
        url = os.path.join(url, "job-output.json")
        try:
            return requests.get(url).json()
        except:
            print("error:", url)
            raise

    list(map(print, play_times([
        (args.provider0, get_log(args.log_url_job0)),
        (args.provider1, get_log(args.log_url_job1)),
    ])))
