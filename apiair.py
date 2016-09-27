#!/usr/bin/env python3
# coding: utf-8

"""Air Quality API."""


import os
import re
import base64
import json
import random
import pandas
import tinydb
from version import version
import colorutils
from flask import Flask, jsonify, request
from flask.ext.autodoc import Autodoc
from simplecrypt import decrypt
from geopy.distance import vincenty


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


def strip_with_indent(s):
    """Remove extra space in code.

    :param s: string.
    :return: string.
    """
    # Find the length of first indentation
    fl = s.split('\n')[0].replace('\t', '    ')
    ni = len(fl) - len(fl.lstrip())

    # Remove all extra indentation
    return "\n".join([l[ni:] for l in s.split('\n')])


@app.template_filter('doc')
def filter_docstring(s):
    """Specific filter for docstring."""
    # Replace ":param var: some text" in "<li>var</li>: some text"
    expr = ':param(.*):(.*)'
    extr = re.findall(expr, s)
    origs = [":param{}:{}".format(*e) for e in extr]
    news = ["<li><u>{}</u>:{}</li>".format(*e) for e in extr]

    if len(news):
        news[0] = "<ul class='params'>" + news[0]
        news[-1] += "</ul>"

    for orig, new in zip(origs, news):
        s = s.replace(orig, new)

    # Replace ".. some code .." in "<code> some code .."
    # Remove extra indentation in <pre>
    s = s.replace('...', '%%%')  # keep '...' safe !
    poss = [m.start() for m in re.finditer('\.\.', s)]  # find position of all '..'
    poss = [(poss[i], poss[i + 1]) for i in range(0, len(poss), 2)]  # group by 2 elements
    for p1, p2 in poss[::-1]:  # reverse list:
        code = s[p1+2:p2]
        ni = len(code.replace('\n', '')) - len(code.replace('\n', '').lstrip())
        clean = '<pre>' + '\n'.join([e[ni:] for e in code.split('\n') if e]) + '</pre>'
        s = s[:p1] + '\n' + clean + s[p2+2:]

    # Restore '...' and replace all nl with br.
    s = s.replace('%%%', '...').replace('\n', '<br />')

    return s


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
    """Information about API (version).

    Response in JSON format:
    ..
    {
      "status": "ok",
      "version": 0.3
    }
    ..
    """
    return jsonify(dict(status='ok', version=version))


@app.route('/post/iqa/<region>', methods=['POST'])
def post_iqa(region):
    """Save last air quality information (index, color) into database.

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
def post_conc(region):
    """Save air quality data into local file.

    :param region: name of region.
    """
    encstr = request.form['data']

    with open(fndat.format(region=region), 'w') as f:
        f.write(decrypt(key, base64.b64decode(encstr)).decode('utf-8'))

    return jsonify(dict(status='ok'))


@app.route('/get/iqa/random')
@autodoc.doc()
def get_iqa_random():
    """Get random colors.

    Examples of use:
    ..
        /get/iqa/random
    ..

    Response in JSON format:
    ..
    {
      "color": [255, 128, 0]
    }
    ..
    """
    # Random color in hue
    h, s, v = random.randint(0, 359), 1.0, 1.0
    c = colorutils.Color(hsv=(h, s, v))
    r, g, b = [int(e) for e in c.rgb]
    return jsonify(dict(color=[r, g, b]))


@app.route('/get/iqa/<region>/<listzoneiqa>')
@autodoc.doc()
def get_iqa_listzoneiqa(region, listzoneiqa):
    """Get latest air quality information (index, color, concentrations).

    :param region: name of region.
    :param listzoneiqa: list of zone and iqa as string like 'zone1-typo1,zone1-typo2,...'

    Examples of use:
    ..
        /get/iqa/paca/aix-urb
        /get/iqa/paca/marseille-urb,marseille-trf
    ..

    Response in JSON format:
    ..
    {
      "color": [
        [ 255, 0, 0 ],
        [ 255, 0, 0 ]
      ],
      "concentrations": [
        {
          "NO2": 26.0,
          "O3": 147.0,
          "PM10": 26.125
        },
        {
          "NO2": 109.0,
          "O3": null,
          "PM10": 32.46
        }
      ],
      "iqa": [
        81.67,
        64.97
      ]
    }
    ..

    """
    # Special case with London (with no colors)
    # /get/iqa/london/urb,trf
    if region == 'london':
        from libapiair import LondonAirQuality, londoncolor
        laq = LondonAirQuality()
        iqas = laq.get_hourly_air_quality_index('cityoflondon')
        print(iqas)
        colors = [londoncolor(iqa) for iqa in iqas]
        return jsonify(dict(iqa=iqas, color=colors))

    db = tinydb.TinyDB(fndb.format(region=region), default_table='air')
    q = tinydb.Query()

    iqas, colors, concs = list(), list(), list()
    for zonetypo in listzoneiqa.strip().split(','):
        zone, typo = zonetypo.strip().split('-')
        enr = db.search((q.zone == zone) & (q.typo == typo))

        if not enr:
            return jsonify(
                dict(status='error: cannot find data for zone={zone} and typo={typo}'.format(
                    **locals()))), 400

        df = pandas.DataFrame(enr).dropna()
        iqa = df['iqa'].max()  # max of each pollutant
        conc = dict(zip(df['pol'].tolist(), df['val'].tolist()))
        for pol in ('NO2', 'PM10', 'O3'):
            if pol not in conc:
                conc[pol] = None

        iqas.append(iqa)
        colors.append(colorize(iqa, param='iqa'))
        concs.append(conc)

    return jsonify(dict(iqa=iqas, color=colors, concentrations=concs))


@app.route('/get/iqa/<region>/<float:lon>,<float:lat>')
@autodoc.doc()
def get_iqa_geoloc(region, lon, lat):
    """Get latest air quality information (index, color, concentrations)
    from geolocation.

    :param region: name of region.
    :param lon: longitude (degrees).
    :param lat: latitude (degrees).

    Example of use:
    ..
        /get/iqa/paca/5.6375,43.6377
    ..

    Response in JSON format:
    ..
    {
      "color": [
        [ 255, 0, 0 ]
      ],
      "concentrations": [
        {
          "NO2": 26.0,
          "O3": 147.0,
          "PM10": 26.125
        }
      ],
      "iqa": [
        81.67
      ]
    }
    ..
    """
    # FIXME: this is a testing function.

    aix = (5.454025, 43.531127)
    marseille = (5.369889, 43.296346)

    loc = (lon, lat)  # location of user
    d_aix = vincenty(loc, aix).kilometers
    d_marseille = vincenty(loc, marseille).kilometers

    if d_aix < d_marseille:
        return get_iqa_listzoneiqa(region, 'aix-urb')
    else:
        return get_iqa_listzoneiqa(region, 'marseille-urb')


@app.route('/get/conc/<region>/<listmesures>')
@autodoc.doc()
def get_conc_listmesures(region, listmesures):
    """Get air quality data.

    :param region: name of region.
    :param listmesures: list of measure names as string like 'mes1,mes2,...'

    Examples of use:
    ..
        /get/conc/paca/N2CINQ
        /get/conc/paca/PCCINQ,PCAIXA
    ..

    Response in JSON format:
    ..
    {
      "data": {
        "N2CINQ": [
          7.0,
          4.0,
          6.0,
          ...
        ],
        ...
      },
      "index": [
        "2016-09-07 01:00:00",
        "2016-09-07 02:00:00",
        "2016-09-07 03:00:00",
         ...
      ],
      "status": "ok"
    }
    ..
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
    """Documentation."""
    return autodoc.html(title='apiair documentation', template='documentation.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
