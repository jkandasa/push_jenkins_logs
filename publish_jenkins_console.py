"""This program collects Jenkins builds and posts the console log to fpaste.org"""
import argparse
import json
import os
import re
import sys
from collections import OrderedDict

import requests
import urllib
from requests.exceptions import ConnectionError
from jenkinsapi.jenkins import Jenkins

# api key copied from: https://pagure.io/fpaste/blob/513d53d67502a2f21abe5d9b868b79dc53bc3a76/f/fpaste#_34
APIKEY = urllib.urlencode({'apikey': '5uZ30dTZE1a5V0WYhNwcMddBRDpk6UzuzMu-APKM38iMHacxdA0n4vCqA34avNyt'})
FPASTE_URL = 'https://paste.centos.org/api/create?' + APIKEY

# comment log content in md file
COMMENT_MD_FILE = 'build_comment_log.md'
if 'WORKSPACE' in os.environ:
    COMMENT_MD_FILE = '{}/{}'.format(os.environ['WORKSPACE'], COMMENT_MD_FILE)

_PARSER = argparse.ArgumentParser()
_PARSER.add_argument(
    '--hostname', '-H', help="Jenkins server hostname with port, http://localhost:8080",
    type=str, default="http://localhost:8080")
_PARSER.add_argument('--username', '-U', help="Username of the server", type=str, default=None)
_PARSER.add_argument('--password', '-P', help="Password of the server", type=str, default=None)
_PARSER.add_argument('--ssl_verify', '-ssl', help="Verify SSL", type=bool, default=False)
_PARSER.add_argument('--job_name', '-jn', help="Jenkins job name", type=str, required=True)
_PARSER.add_argument('--build_number', '-bn', help="Build number", type=int, required=True)
_PARSER.add_argument('--omit_success_logs', '-ol', help="Whether to omit logs of successful builds", action="store_true")
_PARSER.add_argument(
    '--filter', '-f', help="Regular expression to filter jobs",
    type=str, default=r'[\w-]+ #\d+')
_PARSER.add_argument(
    '--filter_output', '-fo', help="Regular expression to filter output",
    type=str, default=r'[\w-]+')

# receive arguments from command line
_ARGS = _PARSER.parse_args()

# create Jenkins server client
JENKINS = Jenkins(
    _ARGS.hostname, username=_ARGS.username, password=_ARGS.password, ssl_verify=_ARGS.ssl_verify)
try:
    # get build details
    BUILD = JENKINS[_ARGS.job_name].get_build(buildnumber=_ARGS.build_number)
except ConnectionError as e:
    print(e)
    with open(COMMENT_MD_FILE, mode="w") as _FILE:
        _FILE.write('PRT Failed, Please Contact QE')
    sys.exit()

# print job filter pattern
print 'Job Filter pattern: "{}"'.format(_ARGS.filter)

# print output filter pattern
print 'Output Filter pattern: "{}"'.format(_ARGS.filter_output)

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
    'UNSTABLE': ':question:',
    'ABORTED': ':black_circle:'
    }


def _update_builds(console_log):
    for _job in _get_jobs(console_log):
        _name, _id = _job.split(' #')
        _id = int(_id)
        if _name in JENKINS.keys():
            if _name not in ALL_BUILDS:
                ALL_BUILDS[_name] = set()
            # cover cases when the console log contains refrence to itself which would lead to endless recursion
            if _id in ALL_BUILDS[_name]:
                continue
            ALL_BUILDS[_name].add(_id)
            _build = _get_build(_name, _id)
            _update_builds(_build.get_console())


def _update_build_statuses():
    for _name, _ids in ALL_BUILDS.items():
        BUILD_STATUS[_name] = 'SUCCESS'
        for _id in _ids:
            _build = _get_build(_name, _id)
            _status = _get_status(_build)
            if _status == 'FAILURE':
                BUILD_STATUS[_name] = _status
                break
            elif _status != 'SUCCESS':
                BUILD_STATUS[_name] = _status


def _get_status(_build):
    return _build.get_status().upper()


def _get_jobs(console_log):
    pattern = re.compile(_ARGS.filter)
    data = pattern.findall(console_log)
    return data


def _get_build(_name, _number):
    return JENKINS[_name].get_build(buildnumber=_number)


def _upload_console_log(_name, _ids):
    _content = ""
    for _id in _ids:
        _build = _get_build(_name, _id)
        if _ARGS.omit_success_logs and _get_status(_build) == 'SUCCESS':
            print("Omitting log for job: {}, run: {}".format(_name,_id))
            continue
        _content += _build.get_console().replace('\n', '\n')
    if len(_content) == 0:
        return None

    # check data size
    _data = urllib.urlencode({'title': '{}: #{} part {}'.format(_name, _ids, 1),
        'text': _content,
        'expire': '1440', # 1day
        'lang' : 'text'})
    # 512KiB appears to be the current hard limit (20110404); old limit was 16MiB
    _pasteSizeKiB = len(_data)/1024.0
    if _pasteSizeKiB > 512:
        print("Warning: Paste size is big ({}KiB), pastes > 512KiB are not allowed, dividing to multiple pastes...".format(_pasteSizeKiB))

    # divide and upload in chunks
    _n = 512 * 1024
    _chunks = [_content[i:i+_n] for i in range(0, len(_content), _n)]
    _urls = ""
    for i in range(len(_chunks)):
        _data = urllib.urlencode({'title': '{}: #{} part {}'.format(_name, _ids, i + 1),
            'text': _chunks[i],
            'expire': '1440', # 1day
            'lang' : 'text'})
        _response = requests.post(
            FPASTE_URL, headers={'Content-Type': 'application/x-www-form-urlencoded'}, data=_data.encode('ascii'))
        if _response.status_code == 200:
            _urls += _response.text.rstrip() + " "
        else:
            print('Failed to push the data for the job[name:{}, build_number:{}, response: {}]'.format(
                _name, _ids, _response.text.encode(encoding="utf-8", errors="ignore")))
    return _urls


# update primary build to dict
ALL_BUILDS[_ARGS.job_name] = set()
ALL_BUILDS[_ARGS.job_name].add(_ARGS.build_number)
# update primary build status
BUILD_STATUS[_ARGS.job_name] = _get_status(BUILD)
# update nested build details
_update_builds(BUILD.get_console())
# update status of all builds
_update_build_statuses()
# print details on console
print ALL_BUILDS
print BUILD_STATUS

# upload console logs to fpaste
for _name, _ids in ALL_BUILDS.items():
    # convert to list to have nicer print output
    _ids_list = list(_ids)
    _url = _upload_console_log(_name, _ids_list)
    if not _url:
        _url = "Log omitted"
    print '{} #{} => {}'.format(_name, _ids_list, _url)
    LOGS_URL[_name] = _url
# formate comment log to upload on GitHub
_FINAL_LOG = 'Jenkins CI: {} [#{}]({})'.format(
    _ARGS.job_name, _ARGS.build_number,
    LOGS_URL[_ARGS.job_name])
_LOG_EXISTS = False
_output_pattern = re.compile(_ARGS.filter_output)
for _j_name, _j_ids in ALL_BUILDS.items():
    # convert to list to have nicer print output
    _j_ids_list = list(_j_ids)
    if _j_name != _ARGS.job_name and _output_pattern.match(_j_name):
        _LOG_EXISTS = True
        _FINAL_LOG = _FINAL_LOG + '\n  * {} {} [#{}]({})'.format(
            ICONS[BUILD_STATUS[_j_name]], _j_name, _j_ids_list, LOGS_URL[_j_name])
if not _LOG_EXISTS:
    _FINAL_LOG = _FINAL_LOG + '\n {} PRT Failed, Please Contact QE'.format(
        ICONS['FAILURE'])
# write formatted log into a file
with open(COMMENT_MD_FILE, mode="w") as _FILE:
    _FILE.write(_FINAL_LOG)
# print comment content file location
print '\nBuild comment content file: {}\n'.format(COMMENT_MD_FILE)
