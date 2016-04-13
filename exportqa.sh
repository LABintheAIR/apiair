#!/bin/bash

source $HOME/.path

rootdir=$( dirname $0 )
cd ${rootdir}

log=exportqa.log
echo "--- $( date ) ---" >>${log}
python3.5 exportqa.py 1>>${log} 2>>${log}
echo >>${log}
