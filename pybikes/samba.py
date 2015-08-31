# -*- coding: utf-8 -*-
# Original work Copyright (C) 2014, iomartin <iomartin@iomartin.net>
# Modified work Copyright (C) 2015 Eduardo Mucelli Rezende Oliveira <edumucelli@gmail.com>
# Distributed under the LGPL license, see LICENSE.txt

from .base import BikeShareSystem, BikeShareStation
from . import utils

import re
import ast

__all__ = ['Samba', 'SambaNew', 'SambaStation']

USERAGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/31.0.1650.63 Chrome/31.0.1650.63 Safari/537.36"

class BaseSystem(BikeShareSystem):
    meta = {
        'system': 'Samba',
        'company': ['Mobilicidade Tecnologia LTD', 'Grupo Serttel LTDA']
    }

class Samba(BaseSystem):
    sync = True
    _STATIONS_RGX = 'exibirEstacaMapa\((.*?)\);'

    def __init__(self, tag, meta, url):
        super(Samba, self).__init__(tag, meta)
        self.feed_url = url

    def update(self, scraper = None):
        if scraper is None:
            scraper = utils.PyBikesScraper()
        scraper.setUserAgent(USERAGENT)

        html_data = scraper.request(self.feed_url)
        # clean the data up
        html_data = ''.join(html_data).replace('\n', '').replace('\r', '').replace('"', '')

        stations = re.findall(Samba._STATIONS_RGX, html_data)

        self.stations = []

        # The regex will also match for a function defined in the html. This
        # function is in the position of the array, and thus the [:-1]
        for station in stations[:-1]:
            data = station.split(',')
            name, latitude, longitude, bikes, free, online_status, operation_status = data[3], float(data[0]), float(data[1]), int(data[7]), int(data[8]) - int(data[7]), data[5], data[6]
            extra = {
                'address': data[9],
                'uid': int(data[4]),
                'slots': int(data[8])
            }
            self.stations.append(SambaStation(name, latitude, longitude, bikes, free, online_status, operation_status, extra))

class SambaNew(BaseSystem):
    sync = True
    _STATIONS_RGX = "var\ beaches\ =\ \[(.*?)\,\];"

    def __init__(self, tag, meta, url):
        super(SambaNew, self).__init__(tag, meta)
        self.feed_url = url

    def update(self, scraper = None):
        if scraper is None:
            scraper = utils.PyBikesScraper()
        scraper.setUserAgent(USERAGENT)

        html = scraper.request(self.feed_url)

        stations_html = re.findall(SambaNew._STATIONS_RGX, html)
        stations = ast.literal_eval(stations_html[0])
        '''
        Different from the original Samba class, th new one deals receives stations' information in the following format:
        [(0) name, (1) latitude, (2) longitude, (3) address, (4) address main line, (5) onlineStatus, (6) operationStatus, (7) available bikes (variable not being used in their code) 
            (8) available bikes, (9) available bike stands, (10) internal station status, (11) path to image file, (12) stationId]
        '''
        self.stations = []
        for station in stations:
            name, latitude, longitude, bikes, free, online_status, operation_status = station[0], station[1], station[2], station[8], station[9], station[5], station[6]
            extra = {
                'address': station[4],
                'description': station[3]
            }
            self.stations.append(SambaStation(name, latitude, longitude, bikes, free, online_status, operation_status, extra))

class SambaStation(BikeShareStation):
    def __init__(self, name, latitude, longitude, bikes, free, online_status, operation_status, extra = {}):
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.bikes = bikes
        self.free = free
        self.extra = extra
        self.extra['status'] = self.get_status(online_status, operation_status)

    def get_status(self, onlineStatus, operationStatus):
        # This is based on a function defined in the scrapped ASP page
        if operationStatus == 'EI' or operationStatus == 'EM':
            return 'maintenance/implementation'
        elif onlineStatus == 'A' and operationStatus == 'EO':
            return 'open'
        else:
            return 'closed'