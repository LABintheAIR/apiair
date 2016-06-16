#!/bin/bash

source $HOME/.path

rootdir=$( dirname $0 )
cd ${rootdir}

log=exportqa.log
echo "--- $( date ) ---" >>${log}
python3.5 exportqa.py http://papillon-jnth.rhcloud.com 1>>${log} 2>>${log}
echo >>${log}
python3.5 exportqa.py http://j6tron.labintheair.cc 1>>${log} 2>>${log}
echo >>${log}
