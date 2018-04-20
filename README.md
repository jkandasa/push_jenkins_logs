# push_jenkins_logs
Push Jenkins console logs to fpaste.org


#### Script to be added on Jenkins post run:
```
git clone https://github.com/Kiali-QE/push-jenkins-logs
cd push_jenkins_logs
virtualenv .env
source .env/bin/activate
pip install -r requirements.txt 
python push_jenkins_logs.py -H ${JENKINS_URL} -jn ${JOB_NAME} -bn ${BUILD_NUMBER}
cat ${WORKSPACE}/commit_log.md
```
