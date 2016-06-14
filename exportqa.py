#!/usr/bin/env python3.5
# coding: utf-8

"""Air PACA air quality data."""


import os
import base64
import datetime
import json
import requests
import pandas
import pyair
import yaml
from pprint import pprint
from tabulate import tabulate


# Configuration pour le calcul de l'indice
cfgiqa = {'NO2': 200, 'PM10': 50, 'O3': 180}

# Lecture de la configuration
with open("pacaqa.yml") as f:
    cfg = yaml.load(f.read())

# Dates
now = datetime.datetime.now()
d2 = datetime.date.today()
d1 = d2 - datetime.timedelta(days=1)

# Connection à la base de données
xr = pyair.xair.XAIR(adr=os.environ['XR_HOST'],
                     user=os.environ['XR_USER'],
                     pwd=os.environ['XR_PASSWORD'])

# Lecture des données
datas = dict()
rows = list()
for zone, nfozone in cfg.items():
    datas[zone] = dict()

    for typo, nfotypo in nfozone.items():
        datas[zone][typo] = dict()

        for pol, mesures in nfotypo.items():
            mesures = [e.strip() for e in mesures.strip().split(',')]
            dat = xr.get_mesures(mes=mesures, debut=d1, fin=d2).dropna().mean(axis=1)

            if pol == 'PM10':
                # Moyenne glissante
                dat = pandas.rolling_mean(dat, window=24, min_periods=18).dropna()

            # Lecture de la dernière données disponible
            val = dat.ix[-1]
            dh = dat.index[-1].to_pydatetime()
            # FIXME: alerte si données trop ancienne

            rows.append((zone, typo, pol, dh, val, val / cfgiqa[pol] * 100.))

            # Enregistrement de la donnée
            datas[zone][typo][pol] = (val, val / cfgiqa[pol] * 100.)

# Affichage des données
print(tabulate(rows, headers=('zone', 'typo', 'pol', 'dh', 'val', 'iqa'), numalign="right",
               floatfmt=".0f"))
print()
print("datas:")
pprint(datas)
print()

# Export des données
print("send data:")
encstr = base64.b64encode(json.dumps(datas).encode('utf-8'))
if os.environ['USER'] != 'jv':  # prod
    r = requests.post('http://papillon-jnth.rhcloud.com/post/v2/data', data={'data': encstr})
else:  # test
    r = requests.post('http://localhost:5026/post/v2/data', data={'data': encstr})
print(" | status_code:", r.status_code)
print(" | content:")
print(r.content.decode('utf-8'))

xr.disconnect()
