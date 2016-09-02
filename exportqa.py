#!/usr/bin/env python3.5
# coding: utf-8


"""Air PACA air quality data."""


import base64
import datetime
import json
import logging
import os
import pprint
import sys

import pandas
import pyair
import requests
import yaml
from tabulate import tabulate

# Log
log = logging.getLogger('exportqa')
log.setLevel(logging.DEBUG)

lc = logging.StreamHandler()
lc.setFormatter(logging.Formatter(fmt='[{asctime}] {levelname:8} | {message}',
                                  datefmt='%Y-%m-%d %H:%M:%S', style='{'))
log.addHandler(lc)
del lc

# Arguments
host = sys.argv[1]
log.debug("host is {}".format(host))

# Configuration pour le calcul de l'indice
cfgiqa = {'NO2': 200, 'PM10': 50, 'O3': 180}

# Lecture de la configuration
with open("pacaqa.yml") as f:
    cfg = yaml.load(f.read())

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
# Connection à la base de données
xr = pyair.xair.XAIR(adr=adr, user=user, pwd=pwd)
log.debug("database connection {}@{} ok".format(user, adr))

# Lecture des données
datas = dict()
rows = list()
for zone, nfozone in cfg.items():
    datas[zone] = dict()

    for typo, nfotypo in nfozone.items():
        datas[zone][typo] = dict()

        for pol, mesures in nfotypo.items():
            mesures = [e.strip() for e in mesures.strip().split(',')]
            dat = xr.get_mesures(
                mes=mesures, debut=d1, fin=d2).dropna().mean(axis=1)
            log.debug("get mesures of {}: found {} hourly data".format(
                mesures, len(dat)))

            if pol == 'PM10':
                # Moyenne glissante
                dat = pandas.rolling_mean(dat,
                                          window=24,
                                          min_periods=18).dropna()
                log.debug("PM10: apply 24h rolling mean...")

            if dat.empty:
                log.debug("no data for these mesures !")
                rows.append((zone, typo, pol, None, None, None))
                datas[zone][typo][pol] = (None, None)

            else:
                # Lecture de la dernière données disponible
                val = dat.ix[-1]
                dh = dat.index[-1].to_pydatetime()
                # FIXME: alerte si données trop ancienne

                # Enregistrement de la donnée
                rows.append(
                    (zone, typo, pol, dh, val, val / cfgiqa[pol] * 100.))
                datas[zone][typo][pol] = (val, val / cfgiqa[pol] * 100.)

# Affichage des données
result_table = tabulate(rows,
                        headers=('zone', 'typo', 'pol', 'dh', 'val', 'iqa'),
                        numalign="right", floatfmt=".0f", missingval='--')
log.info("result:\n" + result_table)

log.info("datas:\n" + pprint.pformat(datas))

# Export des données
log.debug("send data to {} ...".format(host))
encstr = base64.b64encode(json.dumps(datas).encode('utf-8'))
r = requests.post(host + '/post/v2/data', data={'data': encstr})
log.debug("status_code: {}".format(r.status_code))
log.debug("content:\n" + r.content.decode('utf-8'))

xr.disconnect()
