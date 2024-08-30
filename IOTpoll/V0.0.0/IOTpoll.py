#!/usr/bin python3

from http.server import BaseHTTPRequestHandler, HTTPServer
from prometheus_client import start_http_server, Gauge

from urllib import parse
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
#from systemd import journal
import Adafruit_DHT
import logging
import socketserver

Ddir='/sys/bus/w1/devices/'
configPOLL = configparser.ConfigParser()
configPINS = configparser.ConfigParser()
KillSwitch = True
POLLlst={"DEF":0}
GaugeW1={"DEF":20}   # W1 Sensors
GaugePIN={"DEF":20}  # Activate Pins
Vers='1.0.2'
MID='XX'
#global PortNo
#global POLLgap

# List all W1 sensors
def LISTwire1():
    SIDs=[]
    devicelist = glob.glob(Ddir+'28*')    
    if devicelist=='':
        return SIDs
    else:
        for device in devicelist:
            TT=device.split("/")
            SID = TT[len(TT)-1]
            SIDs.append('W_S'+SID[3:])
    return SIDs

# Get Sensor Reading
def GETwire1(SID):
    devicefile=Ddir+SID+'/w1_slave'
    try:
        fileobj = open(devicefile,'r')
        lines = fileobj.readlines()
        fileobj.close()
    except:
        return devicefile+" Not Found"

    # get the status from the end of line 1 
    status = lines[0][-4:-1]

    # is the status is ok, get the temperature from line 2
    if status=="YES":
        equals_pos = lines[1].find('t=')
        temp_string = lines[1][equals_pos+2:]
        tempvalue=float(temp_string)/1000
        return tempvalue
    else:
        return -999


# Return Pin ON/OFF status
def RelayGET(PIN):
    #GPIO.setwarnings(False) 
    #GPIO.setmode(GPIO.BCM)
    #GPIO.setup(int(PIN), GPIO.OUT)
    if GPIO.input(int(PIN)):
        return 1  
    else:
        return 0   
    sys.stdout.flush()

# set Pin
def initRLY(tsk):
    GPIO.setwarnings(False) 
    GPIO.setmode(GPIO.BCM)
    for pin in configPINS:
        if pin != 'DEFAULT':
            if configPINS[pin]["Type"]=='Relay':
                SendMSG('TYPE:RELAY'+'-'+str(pin)+' '+configPINS[pin]['NAME']+' Initialised')
                GPIO.setup(int(pin), GPIO.OUT)
                GPIO.output(int(pin), GPIO.HIGH)

# Toggle Pin
def RelayTOGGLE(PIN):
    #GPIO.setwarnings(False) 
    #GPIO.setmode(GPIO.BCM)
    #GPIO.setup(int(PIN), GPIO.OUT)
    if RelayGET(PIN):
       GPIO.output(int(PIN), GPIO.LOW)
       return "0"
    else:
       GPIO.output(int(PIN), GPIO.HIGH)
       return "1"        
    sys.stdout.flush()  

def DelPromethues(typ,key):
    global GaugePIN
    global GaugeW1
    Mkey = MID + '_' + key
    SendMSG('DEL:'+Mkey+' - '+typ+' - '+key )    
    if typ=='W1' and key in GaugeW1:
        GaugeW1.pop(key)
    elif  typ=='PIN' and key in GaugePIN:
        GaugePIN.pop(key)

def UpdPromethues(typ,key,val):
    global GaugePIN
    global GaugeW1
    Mkey = MID + '_' + key
    if not isSetPromethues(typ,key):
        AddPromethues(typ,key)
        SendMSG('New '+typ+' Allocation : '+key)

    #SendMSG('UPD:'+Mkey+' - '+typ+' - '+key+' = '+str(val) )    
    if typ=='W1' and key in GaugeW1:
        GaugeW1[key].set(val)
    elif  typ=='PIN' and key in GaugePIN:
        GaugePIN[key].set(val)

def AddPromethues(typ,key):
    global GaugePIN
    global GaugeW1
    Mkey = MID + '_' + key
    SendMSG('ADD:'+Mkey+' - '+typ+' - '+key)
    if  typ == 'W1' and not key in GaugeW1:
        GaugeW1[key]=Gauge(Mkey,key)
    elif typ == 'PIN' and not key in GaugePIN:
        GaugePIN[key]=Gauge(Mkey,key)
            
def isSetPromethues(typ,key):
    Mkey = MID + '_' + key
    if typ == 'W1' and not key in GaugeW1:
        return False
    elif typ == 'PIN' and not key in GaugePIN:
        return False
    else:
        return True

def ValidatePARMS():
    configPOLL.read('POLL.ini')
    configPINS.read('PINS.ini')
    if "location" not in configPOLL["POLL"]:
        SendMSG('location missing from Config - Job Terminated')
        return False
    if "name" not in configPOLL["POLL"]:
        SendMSG('name missing from Config - Job Terminated')
        return False
    return True    

def SendMSG(msg):
    print(msg)
    #journal.send(msg)   

def ReportPARMS():
    global MID
    global PortNo
    global POLLgap
    print("Location     : ",configPOLL["POLL"]["location"])
    print("Name         : ",configPOLL["POLL"]["name"])
    SendMSG(configPOLL["POLL"]["name"]+' / '+configPOLL["POLL"]["name"])
    MID=configPOLL["POLL"]["location"]+'_'+configPOLL["POLL"]["name"]+'_V2'
    SendMSG('Promethues Prefix : '+MID)

    PortNo=8010
    if "port" in configPOLL["POLL"]: 
        PortNo=int(configPOLL['POLL']['port'])
    SendMSG('Listening on Port : ' + str(PortNo) )

    POLLgap=30
    if "Time" in configPOLL["POLL"]:
        POLLgap=int(configPOLL['POLL']['Time'])

    SendMSG('Poll Intervals : '+str(POLLgap)+' Seconds')
    initRLY('OFF')
    for pin in configPINS:
        if pin != 'DEFAULT':
            if configPINS[pin]["Type"]=='AM2302' or  configPINS[pin]["Type"]=='DHT22':
                SendMSG('TYPE:HUM/TEMP'+'-'+str(pin)+' '+configPINS[pin]['NAME'])

# ---------------------------------------------------------------------------

# GPIO API controller
class gpioHTTPServer_RequestHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self): 
        print("GPIO API Call received (options)")          
        self.send_response(200)      
        self.send_header('Access-Control-Allow-Origin', '*')                
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With") 

    def do_GET(self):
        print("GPIO API Call received - GET")
        self.send_response(200)
        self.send_header('Content-type','text/plain')
        self.end_headers()
        Rsn=APIincoming(self.path)   
        self.wfile.write(bytes(Rsn, "utf8"))

    def do_POST(self):
        #body = self.rfile.read(int(self.headers.getheader('Content-Length')))
        print("GPIO API Call received - POST")
        #metric_data.extend(json.loads(body))
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(bytes("OK","utf8"))

def APIincoming(url):
    qsp=dict(parse.parse_qsl(parse.urlsplit(url).query))
    #print(qsp)
    if 'API' in qsp:
        RtnTxt=''
    else:
        return 'Security Volation'

    if 'TYP' in qsp:
        if 'RLY' in qsp:
            return apiRELAY(qsp['RLY'])
        else:
            for pin in configPINS:
                if pin != 'DEFAULT':
                    if configPINS[pin]["Type"]=='Relay':
                        if RelayGET(pin)==0:
                            RlyStat='OFF'
                        else:
                            RlyStat='ON'                    
                        RtnTxt=RtnTxt+str(pin)+'('+configPINS[pin]['NAME']+')='+RlyStat+'  '
            return RtnTxt
    else:
        return 'TYP=RLY'

def apiRELAY(RID):
    if RID in configPINS:
        return RelayTOGGLE(RID)
    else:
        print('Relay not found')

    return 'OK'
   
# ---------------------------------------------------------------------------

# main function
# Arg1 = R1(relays) or W1(Wire-1) 
# Arg2 = Get/Put
# Arg3 = Relay number 0-7 or SID or nothing
def main():
    global GaugeW1
    SendMSG('Version '+Vers)
    KillSwitch = ValidatePARMS()
    if KillSwitch:
        ReportPARMS()
        start_http_server(PortNo)

  # Server settings
  # Choose port 8080, for port 80, which is normally used for a http server, you need root access
    server_address = ('', 18100)
    httpd = HTTPServer(server_address, gpioHTTPServer_RequestHandler)
    httpd.socket.settimeout(1)
    httpd.handle_request()
    SendMSG('GPIO API running on 18100')

    while KillSwitch:    
        # Wire-1 Sensor Controls
        SIDs=LISTwire1()

        # Remove Dead Sensors
        for ActSid in GaugeW1:
            if ActSid != 'DEF' and ActSid not in SIDs:
                DelPromethues('W1',ActSid)
                SendMSG('Sensor Lost : '+ActSid)

        # Add New Sensors
        for sid in SIDs:
            if not isSetPromethues('W1',sid):
                AddPromethues('W1',sid)
                SendMSG('New Sensor : '+sid)

        # Read Sensors
        for sid in SIDs:
            val = GETwire1('28-'+sid[3:])
            if val != -999:
                UpdPromethues('W1',sid,val)
            else:
                DelPromethues('W1',sid)
                SendMSG('Sensor Error : '+sid)    

        # Read Pins
        for Pin in configPINS:
            if Pin != "DEFAULT":
                if configPINS[Pin]["Type"]=='AM2302' or configPINS[Pin]["Type"]=='DHT22':
                    humidity,temperature = Adafruit_DHT.read_retry(22, Pin)
                    if isinstance(temperature, float):
                        UpdPromethues('PIN','DHT22_'+Pin+'_TEMP',temperature)
                    if isinstance(humidity, float):
                        UpdPromethues('PIN','DHT22_'+Pin+'_HUM',humidity)

                if configPINS[Pin]["Type"]=='Relay':
                    UpdPromethues('PIN','RELAY_'+Pin,RelayGET(Pin) )

        GapCnt=0
        while GapCnt <= POLLgap:
            time.sleep(1)
            httpd.handle_request()
            GapCnt+=1


    sys.stdout.flush()  

if __name__=="__main__":
    main()
