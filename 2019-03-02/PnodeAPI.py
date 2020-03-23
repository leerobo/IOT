#!/usr/bin python3

# Install this on the prometheus server to accept polling metrics 
# and place them on the node_exporter text file scrapper
 
import configparser 
import json
import time
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
config = configparser.ConfigParser()
PortNO=9117

class MyHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_POST(self):
        ps=self.path.split("/")
        # print("connection from ",self.client_address)
        content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
        if ps[1]=='metrics':
            PostTXN = self.rfile.read(content_length)        # <--- Gets the data itself
            self.respond({'status': 200,"Ptxt":str(PostTXN.decode('UTF-8')) })
        else:
            self.respond({'status': 500}) 
        
    def handle_http(self, status_code, path):
        self.send_response(status_code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        content = config["POLL"]["secret"] # Poll reply
        return bytes(content, 'UTF-8')

    def respond(self, opts):
        postJSON=json.loads(opts['Ptxt']) 
        postURL=self.path.split("/")
        response = self.handle_http(opts['status'], self.path)

        Tsec = time.time()
        FileName=postURL[3]+'_'+postJSON[0]["LID"]+'_'+postJSON[0]["MID"]+'_'+postJSON[0]["SID"]
        # Fname=config["API"]["collectordir"]+"/RPI."+postJSON[0]["LID"]+'.'+postJSON[0]["MID"]+'.'+postJSON[0]["SID"]+".prom"
        Fname=config["API"]["collectordir"]+'/'+FileName+".prom"
        if os.path.exists(Fname):
            os.remove(Fname)
        # print(Fname)

        f = open(Fname, "wt")
        # Version 1 Format
        NodeExp=postURL[3]+'_'+postJSON[0]["LID"]+'_'+postJSON[0]["MID"]+'_'+postJSON[0]["SID"]     # WIRE1
        NodeExp+=' '+postJSON[0]["Value"]+'\n'
        # Version 2 Format 
        #NodeExp2=postJSON[0]["LID"]+'{Type="'+postURL[3]+'",MID="'+postJSON[0]["MID"]+'",SID="'+postJSON[0]["SID"]+'"}'     # WIRE1
        #NodeExp2+=' '+postJSON[0]["Value"]+'\n'

        if (postJSON[0]["SID"][:2] != '28'):
            print(FileName,':',NodeExp)
            f.write(NodeExp)
            f.close
        else:
            print(FileName,' :SUPRESSED: ',NodeExp)

        self.wfile.write(response)
        # print(response)

if __name__ == '__main__':
    config.read('Pnode.ini')
    print("Collector Directory : ",config["API"]["collectordir"])
    print("API Server Port     : ",config["API"]["port"])
    PortNO = int(config["API"]["port"])

    server_class = HTTPServer
    httpd = server_class(('', PortNO), MyHandler)
    print(time.asctime(), 'Server Starts - %s:%s' % ('', PortNO))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print(time.asctime(), 'Server Stops - %s:%s' % ('', config["API"]["port"]))