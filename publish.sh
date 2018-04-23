#!/bin/bash

# Get user current location
USER_LOCATION=$PWD
ACTUAL_LOCATION=`dirname $0`

# Change the location to where exactly python files are located
cd ${ACTUAL_LOCATION}

# create virtual envirnment and activate
virtualenv .env
source .env/bin/activate

# install requirements
pip install -r requirements.txt

# execute python code to publish console logs 
python publish_jenkins_console.py -H ${JENKINS_URL} -jn ${JOB_NAME} -bn ${BUILD_NUMBER}

# print commit file content
cat ${WORKSPACE}/commit_log.md

# back to user location
cd ${USER_LOCATION}

echo -e "\n*** End of publish logs ***\n"