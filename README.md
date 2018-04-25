# Publish Jenkins Console
Publish Jenkins console logs to fpaste.org.
Pass primary job name and build number. Takes all other dependent jobs consoles and publish it on fpaste.org

**IMPORTANT:** Job name should satisfy this pattern: `[\w-]+`


#### Script to be called on Jenkins post run:
```
./publish.sh
```

#### publish_jenkins_console.py usage
```
$ python publish_jenkins_console.py -h
usage: publish_jenkins_console.py [-h] [--hostname HOSTNAME]
                                  [--username USERNAME] [--password PASSWORD]
                                  [--ssl_verify SSL_VERIFY] --job_name
                                  JOB_NAME --build_number BUILD_NUMBER

optional arguments:
  -h, --help            show this help message and exit
  --hostname HOSTNAME, -H HOSTNAME
                        Jenkins server hostname with port,
                        http://localhost:8080
  --username USERNAME, -U USERNAME
                        Username of the server
  --password PASSWORD, -P PASSWORD
                        Password of the server
  --ssl_verify SSL_VERIFY, -ssl SSL_VERIFY
                        Verify SSL
  --job_name JOB_NAME, -jn JOB_NAME
                        Jenkins job name
  --build_number BUILD_NUMBER, -bn BUILD_NUMBER
                        Build number
```
