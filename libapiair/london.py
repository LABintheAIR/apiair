#!/usr/bin/env python3
# coding: utf-8

"""London Air Quality."""


import io
import datetime
import json
import requests
import pandas


class LondonAirQuality(object):
    """London Air Quality."""

    def __init__(self):
        self.baseurl = "http://api.erg.kcl.ac.uk/AirQuality"

    def _read_json(self, apiurl):
        """Read data from API (JSON format)."""
        r = requests.get(self.baseurl + apiurl)
        assert r.status_code == 200
        return json.loads(r.content.decode('utf-8'))

    def _read_csv(self, apiurl):
        """Read data from API (CSV format)."""
        r = requests.get(self.baseurl + apiurl)
        assert r.status_code == 200
        s = io.StringIO(r.content.decode('utf-8'))
        return pandas.read_csv(s)

    def read_measures(self, sitecode, specie, start, end):
        """Read measure datas of a monitoring site.

        :param sitecode: site code of monitoring site.
        :param specie: specie.
        :param start: datetime.date object.
        :param end: datetime.date object.
        :return: pandas.DataFrame.
        """
        apiurl = ('/Data/SiteSpecies/SiteCode={sitecode}/'
                  'SpeciesCode={specie}/'
                  'StartDate={start:%Y-%m-%d}/'
                  'EndDate={end:%Y-%m-%d}/csv').format(**locals())
        df = self._read_csv(apiurl)
        df.columns = ['datetime_gmt', specie]
        df = df.set_index('datetime_gmt')
        return df

    def get_latest_measures(self, sitecode, specie):
        """Return latest measures of a monitoring site.

        :param sitecode: site code of monitoring site.
        :param specie: specie.
        :return: (datetime_gmt, value) or None.
        """
        di = datetime.datetime.today()
        de = di + datetime.timedelta(days=1)
        df = self.read_measures(sitecode, specie, di, de).dropna()
        if df.empty:
            return None
        return df.iloc[-1].name, df.iloc[-1][specie]

    def get_hourly_air_quality_index__datatest(self, groupname):
        """

        :param groupname:
        :return:
        """
        now = datetime.datetime.now()

        apiurl = '/Hourly/MonitoringIndex/GroupName={groupname}/Json'.format(**locals())
        data = self._read_json(apiurl)
        sites = data['HourlyAirQualityIndex']['LocalAuthority']['Site']
        for site in sites:
            sitecode = site['@SiteCode']
            sitetype = site['@SiteType']
            bulletindate = site['@BulletinDate']
            if isinstance(site['Species'], dict):
                species = [site['Species'], ]
            else:
                species = site['Species']
            for specie in species:
                pol = specie['@SpeciesCode']
                idx = specie['@AirQualityIndex']

                print(("{now:%Y-%m-%d %H:%M:%S},{bulletindate},{sitecode},"
                       "{sitetype},{pol},{idx}").format(**locals()))

    def get_hourly_air_quality_index(self, groupname):
        """

        :param groupname:
        :return:
        """
        max_urb, max_trf = 0, 0

        apiurl = '/Hourly/MonitoringIndex/GroupName={groupname}/Json'.format(**locals())
        data = self._read_json(apiurl)
        sites = data['HourlyAirQualityIndex']['LocalAuthority']['Site']
        for site in sites:
            sitecode = site['@SiteCode']
            sitetype = site['@SiteType']
            bulletindate = site['@BulletinDate']
            if isinstance(site['Species'], dict):
                species = [site['Species'], ]
            else:
                species = site['Species']
            for specie in species:
                pol = specie['@SpeciesCode']
                idx = int(specie['@AirQualityIndex'])
                if 'Urban' in sitetype and idx > max_urb:
                    max_urb = idx
                elif 'Roadside' in sitetype and idx > max_trf:
                    max_trf = idx
        return max_urb, max_trf


def londoncolor(idx):
    low = (0, 255, 0)  # green
    moderate = (255, 163, 0)  # orange
    high = (255, 0, 0)  # red

    idx = int(idx)
    if idx < 0:
        idx = 0
    if idx > 10:
        idx = 10
    colors = [None, low, low, low, moderate, moderate, moderate, high, high, high, high]
    return colors[idx]


if __name__ == '__main__':

    # Testing code

    aq = LondonAirQuality()
    aq.get_hourly_air_quality_index__datatest('cityoflondon')
