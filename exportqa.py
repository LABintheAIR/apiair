#!/usr/bin/env python3.5
# coding: utf-8

"""Air PACA air quality data."""


import os
import base64
import datetime
import json
import requests
import numpy
import pandas
import pyair
import yaml

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
iqas = dict()
for zone, nfozone in cfg.items():
    iqas[zone] = dict()

    for typo, nfotypo in nfozone.items():
        iqatypo = list()

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

            print(zone, typo, pol, dh, val, val / cfgiqa[pol])
            iqatypo.append(val / cfgiqa[pol])

        # Agregation par typologie
        iqatypo = numpy.array(iqatypo).max()
        print(zone, typo, '=>', iqatypo)

        # Enregistrement de la donnée
        iqas[zone][typo] = iqatypo

# Export des données
print('iqas =>', iqas)
encstr = base64.b64encode(json.dumps(iqas).encode('utf-8'))
r = requests.post('http://localhost:5000/post/iqa', data={'data': encstr})
print(r.status_code)
print(r.content)


xr.disconnect()
