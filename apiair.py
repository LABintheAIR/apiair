#!/usr/bin/env python3
# coding: utf-8

"""Air Quality API."""


import os
import base64
import json
import pandas
import tinydb
from version import version
from flask import Flask, jsonify, request
from flask.ext.autodoc import Autodoc
from simplecrypt import decrypt


# Dossier des données
datadir = os.environ.get('OPENSHIFT_DATA_DIR', '.')

# Application Flask
app = Flask('apiair')
autodoc = Autodoc(app)  # Autodoc extension

# Stockage des données
fndb = os.path.join(datadir, '{region}_iqa.json')  # iqa, last hour
fndat = os.path.join(datadir, '{region}_conc.dat')  # conc, last two days

# Clé via variable d'environnement
key = os.environ['APIAIR_KEY']


def colorhex_to_rgb(chex):
    """Convert color.

    :param chex: color in hex.
    :return: (r, g, b) tuple with r, g and b as int from 0 to 255.
    """
    if chex.startswith('#'):
        chex = chex[1:]
    return tuple([int(chex[i:i+2], base=16) for i in (0, 2, 4)])


def colorize(v, param):
    """Colorize.

    :param v: value (float).
    :param param: parameter (string).
    :return: (r, g, b) tuple with r, g and b as int from 0 to 255.
    """
    colparams = dict(
        citeair=dict(
            colors=['#79bc6a', '#bbcf4c', '#eec20b', '#f29305', '#960018'],
            limits=[25, 50, 75, 100]  # valeur de la limite, exclus de la classe inférieure
        ),
        iqa_=dict(
            colors=['#32B8A3',
                    '#5CCB60',
                    '#99E600',
                    '#C3F000',
                    '#FFFF00',
                    '#FFD100',
                    '#FFAA00',
                    '#FF5E00',
                    '#FF0000'],
            limits=[.2, .3, .4, .5, .6, .7, .8, .9]
        ),
        iqa=dict(
            colors=['#00ff00', '#ffff00', '#ff5e00', '#ff0000'],
            limits=[.5, .75, .9]
        )
    )

    if param not in colparams:
        raise ValueError("cannot find param '%s'" % param)

    colors, limits = colparams[param]['colors'], colparams[param]['limits']
    limits.append(None)

    for color, limit in zip(colors, limits):
        if limit is None or v < limit:
            return colorhex_to_rgb(color)


@app.route('/')
@autodoc.doc()
def index():
    """Index."""
    return jsonify(dict(status='ok', version=version))


@app.route('/post/iqa/<region>', methods=['POST'])
@autodoc.doc()
def post_iqa(region):
    """Save data into database.

    :param region: name of region.
    """
    db = tinydb.TinyDB(fndb.format(region=region), default_table='air')
    q = tinydb.Query()

    encstr = request.form['data']
    iqas = json.loads(base64.b64decode(encstr).decode('utf-8'))  # decode data

    inserted, updated = 0, 0

    # Save data into database
    for zone, nfozone in iqas.items():
        for typo, nfotypo in nfozone.items():
            for pol, (val, iqa) in nfotypo.items():

                query = (q.zone == zone) & (q.typo == typo) & (q.pol == pol)
                out = db.search(query)
                if out:  # existing into databse: update it
                    db.update({'val': val, 'iqa': iqa}, query)
                    updated += 1
                else:  # insert it
                    db.insert(dict(zone=zone, typo=typo, pol=pol, val=val, iqa=iqa))
                    inserted += 1

    return jsonify(dict(status='ok', inserted=inserted, updated=updated))


@app.route('/post/conc/<region>', methods=['POST'])
@autodoc.doc()
def post_conc(region):
    """Save data into local file.

    :param region: name of region.
    """
    encstr = request.form['data']

    with open(fndat.format(region=region), 'w') as f:
        f.write(decrypt(key, base64.b64decode(encstr)).decode('utf-8'))

    return jsonify(dict(status='ok'))


@app.route('/get/iqa/<region>/<listzoneiqa>')
@autodoc.doc()
def extr_listzoneiqa(region, listzoneiqa):
    """List of IQA as color.

    :param region: name of region.
    :param listzoneiqa: list of zone and iqa as string like 'zone1-typo1,zone1-typo2,...'
    """
    db = tinydb.TinyDB(fndb.format(region=region), default_table='air')
    q = tinydb.Query()

    iqas, colors = list(), list()
    for zonetypo in listzoneiqa.strip().split(','):
        zone, typo = zonetypo.strip().split('-')
        enr = db.search((q.zone == zone) & (q.typo == typo))

        if not enr:
            return jsonify(
                dict(status='error: cannot find data for zone={zone} and typo={typo}'.format(
                    **locals()))), 400

        df = pandas.DataFrame(enr)
        iqa = df['iqa'].max()  # max of each pollutant

        iqas.append(iqa)
        colors.append(colorize(iqa, param='iqa'))

    return jsonify(dict(iqa=iqas, color=colors))


@app.route('/get/conc/<region>/<listmesures>')
@autodoc.doc()
def get_data(region, listmesures):
    """Extract air quality data.

    :param region: name of region.
    :param listmesures: list of measure names as string like 'mes1,mes2,...'
    """
    listmesures = listmesures.strip().split(',')

    # Read data from local file
    dat = pandas.read_csv(fndat.format(region=region))

    idx = dat['dh'].tolist()
    extr = dict()

    for mes in listmesures:
        if mes not in dat:
            return jsonify(dict(status='error', message="cannot find '{}' measure !".format(mes))), 400
        extr[mes] = dat[mes].tolist()

    return jsonify(dict(status='ok', index=idx, data=extr))


@app.route('/doc')
@autodoc.doc()
def doc():
    """API documentation."""
    return autodoc.html(title='apiair documentation', template='documentation.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
