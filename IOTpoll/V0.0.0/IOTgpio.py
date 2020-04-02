#!/usr/bin python3

from http.server import BaseHTTPRequestHandler, HTTPServer
from prometheus_client import start_http_server, Gauge
import RPi.GPIO as GPIO
import configparser 
import time
import http.client
import json

import sys
import os
import time
import datetime
import glob
import socket
from array import array

Vers='1.0.1'

def SendMSG(msg):
    print(msg)
    #journal.send(msg)   

# ---------------------------------------------------------------------------

# GPIO API controller
class gpioHTTPServer_RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        print("GPIO API Call received")
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        message = "Complete!"
        self.wfile.write(bytes(message, "utf8"))
        return

class EchoRequestHandler(socketserver.BaseRequestHandler):
    def __init__(self, request, client_address, server):
        print('__init__')
        socketserver.BaseRequestHandler.__init__(self, request,
                                                 client_address,
                                                 server)
        return

    def setup(self):
        print('setup')
        return socketserver.BaseRequestHandler.setup(self)

    def handle(self):
        print('handle')
        # Echo the back to the client
        data = self.request.recv(1024)
        print('recv()->"%s"', data)
        self.request.send(data)
        return

    def finish(self):
        print('finish')
        return socketserver.BaseRequestHandler.finish(self)

class EchoServer(socketserver.TCPServer):
    def __init__(self, server_address,
                 handler_class=EchoRequestHandler,
                 ):
        self.logger = logging.getLogger('EchoServer')
        self.logger.debug('__init__')
        socketserver.TCPServer.__init__(self, server_address,
                                        handler_class)
        return

    def server_activate(self):
        self.logger.debug('server_activate')
        socketserver.TCPServer.server_activate(self)
        return

    def serve_forever(self, poll_interval=0.5):
        self.logger.debug('waiting for request')
        self.logger.info(
            'Handling requests, press <Ctrl-C> to quit'
        )
        socketserver.TCPServer.serve_forever(self, poll_interval)
        return

    def handle_request(self):
        self.logger.debug('handle_request')
        return socketserver.TCPServer.handle_request(self)

    def verify_request(self, request, client_address):
        self.logger.debug('verify_request(%s, %s)',
                          request, client_address)
        return socketserver.TCPServer.verify_request(
            self, request, client_address,
        )

    def process_request(self, request, client_address):
        self.logger.debug('process_request(%s, %s)',
                          request, client_address)
        return socketserver.TCPServer.process_request(
            self, request, client_address,
        )

    def server_close(self):
        self.logger.debug('server_close')
        return socketserver.TCPServer.server_close(self)

    def finish_request(self, request, client_address):
        self.logger.debug('finish_request(%s, %s)',
                          request, client_address)
        return socketserver.TCPServer.finish_request(
            self, request, client_address,
        )

    def close_request(self, request_address):
        self.logger.debug('close_request(%s)', request_address)
        return socketserver.TCPServer.close_request(
            self, request_address,
        )

    def shutdown(self):
        self.logger.debug('shutdown()')
        return socketserver.TCPServer.shutdown(self)
# ---------------------------------------------------------------------------

# main function
# Arg1 = R1(relays) or W1(Wire-1) 
# Arg2 = Get/Put
# Arg3 = Relay number 0-7 or SID or nothing
def main():
    SendMSG('Version '+Vers)

    server_address = ('127.0.0.1', 18100)
    httpd = HTTPServer(server_address, gpioHTTPServer_RequestHandler)
    httpd.server_activate()
    SendMsg('GPIO API running on 18100')

if __name__=="__main__":
    main()
