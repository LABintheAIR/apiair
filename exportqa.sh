#!/bin/bash

export XR_HOST='172.16.12.30'
export XR_USER='jv'
export XR_PASSWORD='jv'
export APIAIR_KEY='9N9K3p5XEmQhhqnP'

# Python3.5
PYH35=/opt/python-3.5.0
export PATH=${PYH35}/bin:${PATH}
export LD_LIBRARY_PATH=${PYH35}/lib:${LD_LIBRARY_PATH}

# Oracle InstantClient
export ORACLE_HOME=/opt/oracle/instantclient_11_2
export LD_LIBRARY_PATH=${ORACLE_HOME}:${LD_LIBRARY_PATH}



rootdir=$( dirname $0 )
cd ${rootdir}

source env/bin/activate

log=exportqa.log
echo "--- $( date ) ---" >>${log}

python3.5 exportqa.py http://papillon-jnth.rhcloud.com 1>>${log} 2>>${log}
echo >>${log}

python3.5 exportqa_v2.py http://papillon-jnth.rhcloud.com 1>>${log} 2>>${log}
echo >>${log}

python3.5 exportqa.py http://j6tron.labintheair.cc:16500 1>>${log} 2>>${log}
echo >>${log}
