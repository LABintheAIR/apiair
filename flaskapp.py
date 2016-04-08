#!/usr/bin/env python3
# coding: utf-8

"""Berlin Air Quality API."""


import random
from flask import Flask, jsonify


app = Flask('berlinairquality')


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


@app.route('/')
def index():
    """Index."""
    return jsonify(dict(status='ok'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
