#!/usr/bin/env python

from http.server import BaseHTTPRequestHandler, HTTPServer
from functools import partial
import json
import cgi
import sys
from pyezr import pyezr
from threading import Thread
import time
import urllib.parse

result = {}
commandlist = []

class EzrSetTemperatureCommand:
    def __init__(self, ezr, room, target):
        self.ezr = ezr
        self.room = room
        self.target = target

def poll_ezr(config):
    while True:
        print('Poll...')
        ezrs = config['ezr']

        for dev in ezrs:            
            ezr = pyezr.pyezr(config['ezr'][dev])
            if not dev in result:
                result[dev] = {}
            try:
                if ezr.connect():
                    result[dev]['status'] = 'ok'
                else:
                    result[dev]['status'] = 'error'
                    continue
            except:
                result[dev]['status'] = 'error'
                continue

            heatareas = ezr.getHeatAreas()

            for command in commandlist:
                if command.ezr == dev:
                    for ha in heatareas:
                        if ha.getName() == command.room:
                            if command.target != ha.getTargetTemperature():
                                ha.setTargetTemperature(command.target)
                                try:
                                    ezr.save()
                                except:
                                    print('Error saving to EZR')
                            commandlist.remove(command)

            for ha in heatareas:
                result[dev][ha.getName()] = {}
                result[dev][ha.getName()]['number'] = ha.getNumber()
                result[dev][ha.getName()]['actual_temperature'] = ha.getActualTemperature()
                result[dev][ha.getName()]['target_temperature'] = ha.getTargetTemperature()
        print('Done.')
        time.sleep(int(config['interval']))

class Server(BaseHTTPRequestHandler):
    def __init__(self, config, *args, **kwargs):
        self.config = config
        super().__init__(*args, **kwargs)
        
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
    def do_HEAD(self):
        self._set_headers()
        
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/set_target.json':
            req = urllib.parse.parse_qs(parsed.query)
            if 'ezr' in req and 'room' in req and 'target' in req:
                ezr = req['ezr'][0]
                room = req['room'][0]
                target = req['target'][0]
                if ezr in self.config['ezr']:
                    commandlist.append(EzrSetTemperatureCommand(ezr, room, target))
                    if room in result[ezr]:
                        result[ezr][room]['target_temperature'] = target

        self._set_headers()
        self.wfile.write(bytes(json.dumps(result), 'utf-8'))
        
    # POST echoes the message adding a JSON field
    def do_POST(self):
        ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
        
        # refuse to receive non-json content
        if ctype != 'application/json':
            self.send_response(400)
            self.end_headers()
            return
            
        # read the message and convert it into a python dictionary
        length = int(self.headers.getheader('content-length'))
        message = json.loads(self.rfile.read(length))
        
        # add a property to the object, just to mess with data
        message['received'] = 'ok'
        
        # send the message back
        self._set_headers()
        self.wfile.write(json.dumps(message))
        
def run(config=None):
    if not config:
        print('Error loading config')
        sys.exit(1)

    port = config['port']
    server_address = ('', port)
    handler_class = partial(Server, config)
    httpd = HTTPServer(server_address, handler_class)
    poll_thread = Thread(target=poll_ezr, args=(config,))
    poll_thread.start()
    print('Starting httpd on port %d...' % port)
    httpd.serve_forever()
    
if __name__ == "__main__":

    with open("ezr_config.json", "r") as f:
        config = json.load(f)
    print("Config: ", config)

    run(config=config)
