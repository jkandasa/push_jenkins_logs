#!/bin/bash

# Get user current location
USER_LOCATION=$PWD
ACTUAL_LOCATION=`dirname $0`

# Change the location to where exactly python files are located
cd ${ACTUAL_LOCATION}

# install requirements
sudo pip install -r requirements.txt

# set Job filter if it is not available
if [[ -z "${JOB_FILTER}" ]]; then
  JOB_FILTER="[\w-]+ #\d+"
fi

# execute python code to publish console logs 
python publish_jenkins_console.py -H ${JENKINS_URL} -jn ${JOB_NAME} -bn ${BUILD_NUMBER} -f "${JOB_FILTER}" -fo "${OUTPUT_FILTER}"

# print comment file content
cat ${WORKSPACE}/build_comment_log.md

# back to user location
cd ${USER_LOCATION}

echo -e "\n*** End of publish logs ***\n"