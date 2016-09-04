#!/usr/bin/env python3.5
# coding: utf-8


"""Air PACA, export air quality data to distant server."""


import base64
import datetime
import logging
import os
import sys

import pyair
import requests
from simplecrypt import encrypt


# Log
log = logging.getLogger('exportqa_v2')
log.setLevel(logging.DEBUG)

lc = logging.StreamHandler()
lc.setFormatter(logging.Formatter(fmt='[{asctime}] {levelname:8} | {message}',
                                  datefmt='%Y-%m-%d %H:%M:%S', style='{'))
log.addHandler(lc)
del lc

# Arguments
host = sys.argv[1]
log.debug("host is {}".format(host))

# Dates
now = datetime.datetime.now()
d2 = datetime.date.today()
d1 = d2 - datetime.timedelta(days=1)
log.debug("d1 is {d1:%Y-%m-%d %H:%M:%S}, d2 is {d2:%Y-%m-%d %H:%M:%S}".format(
    **locals()))

# Lecture variables d'environnement
adr = os.environ['XR_HOST']
user = os.environ['XR_USER']
pwd = os.environ['XR_PASSWORD']
key = os.environ['APIAIR_KEY']

# Connection à la base de données
xr = pyair.xair.XAIR(adr=adr, user=user, pwd=pwd)
log.debug("database connection {}@{} ok".format(user, adr))

# Lecture de la liste des mesures
mes = xr.liste_mesures(parametre=['NO2', 'O3', 'PM10', 'PM2.5'])
log.debug("read list of measurement : got {n} rows".format(n=len(mes)))

# Lecture des données de concentrations
dat = xr.get_mesures(mes=mes['MESURE'], debut=d1, fin=d2)
dat.index = dat.index.shift(1)  # shift +1 hour to restore orginal data index
log.debug("read data : got {} values".format(dat.shape))

# Encode data
encstr = base64.b64encode(encrypt(key, dat.to_csv(index_label='dh')))

# Export des données
log.debug("send data to {} ...".format(host))
r = requests.post(host + '/post/v2/data_v2', data={'data': encstr})
log.debug("status_code: {}".format(r.status_code))
log.debug("content:\n" + r.content.decode('utf-8'))

xr.disconnect()
