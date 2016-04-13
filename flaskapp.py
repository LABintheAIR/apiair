#!/usr/bin/env python3
# coding: utf-8

"""Papillon Air Quality API."""


import os
import random
import base64
import json
import tinydb
from flask import Flask, jsonify, request


# Application Flask
app = Flask('papillon')

# Base de données pour le stockage des indices
if 'OPENSHIFT_DATA_DIR' in os.environ:
    fndb = os.path.join(os.environ['OPENSHIFT_DATA_DIR'], 'airquality.json')
else:
    fndb = 'airquality.json'

db = tinydb.TinyDB(fndb)
q = tinydb.Query()


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
        iqa=dict(
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
        )
    )

    if param not in colparams:
        raise ValueError("cannot find param '%s'" % param)

    colors, limits = colparams[param]['colors'], colparams[param]['limits']
    limits.append(None)

    for color, limit in zip(colors, limits):
        if limit is None or v < limit:
            return colorhex_to_rgb(color)


@app.route('/test/stations')
def test_stations():
    """Test API (stations)."""
    choices = [(255, 0, 0), (255, 255, 0), (255, 0, 255), (0, 255, 255), (0, 0, 255)]

    tmp = list()
    for i in range(12):
        tmp.append(random.choice(choices))

    data = dict()
    data['NO2'] = tmp

    return jsonify(data)


@app.route('/test/iqa')
def test_iqa():
    """Test API (iqa)."""
    urb = random.randint(15, 60)
    trf = random.randint(urb + 10, 100)

    c_urb, c_trf = colorize(urb, 'citeair'), colorize(trf, 'citeair')

    data = dict()
    data['iqa'] = dict(urb=c_urb, trf=c_trf)

    return jsonify(data)


@app.route('/paca/iqa/<zone>/<typo>')
def paca_iqa(zone, typo):
    """IQA as color."""
    enr = db.search((q.zone == zone) & (q.typo == typo))
    if not enr:
        return jsonify(
            dict(status='error: cannot find data for zone=%s and typo=%s'.format(
                **locals()))), 400

    if len(enr) != 1:
        return jsonify(dict(status='error: corrupt database !')), 400

    iqa = enr[0]['iqa']
    color = colorize(iqa, param='iqa')
    return jsonify(dict(color=color))


@app.route('/paca/iqa/<listzoneiqa>')
def paca_iqa_list(listzoneiqa):
    """List of IQA as color.

    ...?output=color (default)
    ...?output=iqa

    :param listzoneiqa: list of zone and iqa as string like 'zone1-typo1,zone1-typo2,...'
    """
    output = request.args.get('output', 'color')
    outlist = list()
    for zonetypo in listzoneiqa.strip().split(','):
        zone, typo = zonetypo.strip().split('-')
        enr = db.search((q.zone == zone) & (q.typo == typo))

        if not enr:
            return jsonify(
                dict(status='error: cannot find data for zone=%s and typo=%s'.format(
                    **locals()))), 400

        if len(enr) != 1:
            return jsonify(dict(status='error: corrupt database !')), 400

        iqa = enr[0]['iqa']
        if output == 'iqa':
            outlist.append(iqa)
        else:
            outlist.append(colorize(iqa, param='iqa'))
    return jsonify(dict(list=outlist))


@app.route('/')
def index():
    """Index."""
    return jsonify(dict(status='ok'))


@app.route('/post/iqa', methods=['POST'])
def post_iqa():
    """Save IQA data into database."""
    encstr = request.form['data']
    iqas = json.loads(base64.b64decode(encstr).decode('utf-8'))  # decode data

    # Save data into database

    for zone, nfozone in iqas.items():
        for typo, iqa in nfozone.items():

            out = db.search((q.zone == zone) & (q.typo == typo))
            if out:  # existing into databse: update it
                db.update({'iqa': iqa}, (q.zone == zone) & (q.typo == typo))
            else:  # insert it
                db.insert(dict(zone=zone, typo=typo, iqa=iqa))

    return jsonify(dict(status='ok'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
