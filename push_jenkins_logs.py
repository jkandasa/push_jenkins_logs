"""This program collects Jenkins builds and posts the console log to fpaste.org"""
import argparse
import json
import os
import re
from collections import OrderedDict

import requests
from jenkinsapi.jenkins import Jenkins

# fpast url
FPASTE_URL = 'https://paste.fedoraproject.org/api/paste/submit'

# commit log content in md file
COMMIT_MD_FILE = 'commit_log.md'
if os.environ['WORKSPACE']:
    COMMIT_MD_FILE = '{}/{}'.format(os.environ['WORKSPACE'], COMMIT_MD_FILE)

_PARSER = argparse.ArgumentParser()
_PARSER.add_argument(
    '--hostname', '-H', help="Jenkins server hostname with port, http://localhost:8080",
    type=str, default="http://localhost:8080")
_PARSER.add_argument('--username', '-U', help="Username of the server", type=str, default=None)
_PARSER.add_argument('--password', '-P', help="Password of the server", type=str, default=None)
_PARSER.add_argument('--ssl_verify', '-ssl', help="Verify SSL", type=bool, default=False)
_PARSER.add_argument('--job_name', '-jn', help="Jenkins job name", type=str, required=True)
_PARSER.add_argument('--build_number', '-bn', help="Build number", type=int, required=True)

# receive arguments from command line
_ARGS = _PARSER.parse_args()

# create Jenkins server client
JENKINS = Jenkins(
    _ARGS.hostname, username=_ARGS.username, password=_ARGS.password, ssl_verify=_ARGS.ssl_verify)
# get build details
BUILD = JENKINS[_ARGS.job_name].get_build(buildnumber=_ARGS.build_number)

# print Jenkins details
print 'Jenkins Version: {}'.format(JENKINS.version)

# create dict to hold nested builds and it is status
ALL_BUILDS = OrderedDict()
BUILD_STATUS = {}
LOGS_URL = {}
# list of supported emojis in GitHub
# https://gist.github.com/rxaviers/7360908
ICONS = {
    'SUCCESS': ':heavy_check_mark:',
    'FAILURE': ':red_circle:',
    'UNATABLE': ':question:',
    'ABORTED': ':black_circle:'
    }


def _update_builds(console_log):
    for _job in _get_jobs(console_log):
        _name, _id = _job.split(' #')
        _id = int(_id)
        if _name in JENKINS.keys():
            ALL_BUILDS[_name] = _id
            _build = _get_build(_name, _id)
            BUILD_STATUS[_name] = _get_status(_build)
            _update_builds(_build.get_console())


def _get_status(_build):
    return _build.get_status().upper()


def _get_jobs(console_log):
    pattern = re.compile(r'[\w-]+ #\d+')
    data = pattern.findall(console_log)
    return data


def _get_build(_name, _number):
    return JENKINS[_name].get_build(buildnumber=_number)


def _upload_console_log(_name, _number):
    _content = _get_build(_name, _number).get_console().replace('\n', '\n')
    _data = {'title': '{}: #{}'.format(_name, _number), 'contents': _content}
    _response = requests.post(
        FPASTE_URL, headers={'Content-Type': 'application/json'}, data=json.dumps(_data))
    _url = None
    if _response.status_code == 200:
        _url = _response.json()['url']
    else:
        print('Failed to push the data for the job[name:{}, build_number:{}]'.format(
            _name, _number))
    return _url


# update primary build to dict
ALL_BUILDS[_ARGS.job_name] = _ARGS.build_number
# update primary build status
BUILD_STATUS[_ARGS.job_name] = _get_status(BUILD)
# update nested build details
_update_builds(BUILD.get_console())
# print details on console
print ALL_BUILDS
print BUILD_STATUS

# upload console logs to fpaste
for _name, _number in ALL_BUILDS.items():
    _url = _upload_console_log(_name, _number)
    if _url:
        print '{} #{} => {}'.format(_name, _number, _url)
        LOGS_URL[_name] = _url
# formate commit log to upload on GitHub
_FINAL_LOG = '{} Jenkins CI build [#{}]({})'.format(
    ICONS[BUILD_STATUS[_ARGS.job_name]], _ARGS.build_number, LOGS_URL[_ARGS.job_name])
for _j_name, _j_number in ALL_BUILDS.items():
    if _j_name != _ARGS.job_name:
        _FINAL_LOG = _FINAL_LOG + '\n*  {} {} [#{}]({})'.format(
            ICONS[BUILD_STATUS[_j_name]], _j_name, _j_number, LOGS_URL[_j_name])
# write formatted log into a file
with open(COMMIT_MD_FILE, mode="w") as _FILE:
    _FILE.write(_FINAL_LOG)
# print commit content file location
print '\nCommit content file: {}\n'.format(COMMIT_MD_FILE)
