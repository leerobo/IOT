#!/usr/bin python3

# ----------------------------------------------------------------------------
#  IOTpoll cycles thru the connected pins and returns back to Promethus server 
#          the settings,  An API gateway allows grafana pages to switch relays
#          if required
#    
#    To Set : View Readme.txt in folder
#
#    V 1.1.0  -  2020 Mar - Tidy up code 
#  
# ----------------------------------------------------------------------------

import sys
sys.path.append('../Common')

from http.server import BaseHTTPRequestHandler, HTTPServer
from prometheus_client import start_http_server, Gauge

from urllib import parse
import RPi.GPIO as GPIO
import configparser 
import time
import http.client
import json
#from ZigBee import ZBsensors

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
import requests

Ddir='/sys/bus/w1/devices/'
configPOLL = configparser.ConfigParser()
configPINS = configparser.ConfigParser()
KillSwitch = True
POLLlst={"DEF":0}
GaugeINT={"DEF":40}     # Internal Sensors List
Vers='1.1.0'
MID='XX'

# -----------------------------------------------------------------
#    Wire-1 : Wire 1 functions and routines 
# -----------------------------------------------------------------

def LISTwire1():
    SIDs={}
    devicelist = glob.glob(Ddir+'28*')    
    print('devicelist:',devicelist)
    if devicelist=='':
        return SIDs
    else:
        for device in devicelist:
            print(device)
            TT=device.split("/")
            SID = TT[len(TT)-1]
            SIDs['W1_S'+SID[3:]]=GETwire1(TT[len(TT)-1])
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

# -----------------------------------------------------------------
#    Switch Sensors (Doors, Motion, Etc)
# -----------------------------------------------------------------

def LISTswitches(SIDs):

    for pin in configPINS:
        if pin != 'DEFAULT':
            if configPINS[pin]["Type"]=='Motion' or configPINS[pin]["Type"]=='Switch':
                SendMSG(str(pin))
                if GPIO.input(int(pin)):
                    SIDs[int(pin)]=1

    return SIDs

# -----------------------------------------------------------------
#    ZigBee Sensors
# -----------------------------------------------------------------

def ZBpoll():
    global ZBconfig, ZBsensors, ZBsensorC, LockSys
    LockSys = datetime.datetime.today()
    ZBsensorC = ZBsensors(configPOLL["ZIGBEE"]["ip"],configPOLL["ZIGBEE"]["key"])
    return ZBsensorC.GetALL()

    #if 'ZIGBEE' not in configPOLL: return SIDzb
    #params = {"words": 10, "paragraphs": 1, "format": "json"}
    #response = requests.get(f"http://"+configPOLL["ZIGBEE"]["ip"]+"/api/"+configPOLL["ZIGBEE"]["key"]+"/sensors/")
    #if response.status_code != 200:
    #    print("ZigBee Return Error : "+str(response.status_code))
    #    return True
    #ZBc=ZB.ZBsensors(response.json())   #  Store Sensors in ZigBee Class
    #return ZBc.GetALL()

# -----------------------------------------------------------------
#   PIN : Controllers 
# -----------------------------------------------------------------

def PINpoll():
    # Read Pins
    SID={}
    for Pin in configPINS:
        if Pin != 'DEFAULT':
            Sname=configPINS[Pin]['name'].replace(' ','_')
            if configPINS[Pin]["type"]=='AM2302' or configPINS[Pin]["type"]=='DHT22':
                humidity,temperature = Adafruit_DHT.read_retry(22, Pin)
                if isinstance(temperature, float):
                    SID['PIN_DHT22_'+Pin+'_'+Sname+'_TEMP']=temperature
                if isinstance(humidity, float):
                    SID['PIN_DHT22_'+Pin+'_'+Sname+'_HUM']=temperature

            elif configPINS[Pin]["type"]=='relay':
                SID['PIN_RELAY_'+Pin+'_'+Sname]=RelayGET(Pin)

            elif configPINS[Pin]["type"]=='switch':
                SID['PIN_SWITCH_'+Pin+'_'+Sname]=RelayGET(Pin)

            elif configPINS[Pin]["type"]=='motion':
                SID['PIN_MOTION_'+Pin+'_'+Sname]=RelayGET(Pin)
    return SID

# Return Pin ON/OFF status
def RelayGET(PIN):
    if GPIO.input(int(PIN)):
        return 0  
    else:
        return 1   
    sys.stdout.flush()

# Toggle Pin
def RelayTOGGLE(PIN):
    print('Toggle:'+str(RelayGET(int(PIN))))
    if RelayGET(PIN):
       GPIO.output(int(PIN), GPIO.LOW)
       return "0"
    else:
       GPIO.output(int(PIN), GPIO.HIGH)
       return "1"        
    sys.stdout.flush()  

def SETpins():
    GPIO.setwarnings(False) 
    GPIO.setmode(GPIO.BCM)
    for pin in configPINS:
        if pin != 'DEFAULT':
            if configPINS[pin]["type"]=='relay':
                SendMSG('TYPE:RELAY'+'-'+str(pin)+' '+configPINS[pin]['name']+' Initialised')
                GPIO.setup(int(pin), GPIO.OUT)
                GPIO.output(int(pin), GPIO.HIGH)

            if configPINS[pin]["type"]=='AM2302' or  configPINS[pin]["Type"]=='DHT22':
                SendMSG('TYPE:HUM/TEMP'+'-'+str(pin)+' '+configPINS[pin]['name'])

            if configPINS[pin]["type"]=='switch':
                SendMSG('TYPE:SWITCH'+'-'+str(pin)+' '+configPINS[pin]['name']+' Initialised')
                GPIO.setup(int(pin), GPIO.IN, pull_up_down=GPIO.PUD_UP)

            if configPINS[pin]["type"]=='motion':
                SendMSG('TYPE:Motion'+'-'+str(pin)+' '+configPINS[pin]['name']+' Initialised')
                GPIO.setup(int(pin), GPIO.IN, pull_up_down=GPIO.PUD_UP)
             
    #sys.stdout.flush()  

# ------------------------------------------------------------------------
#   Promethues : Comms to Promethus Server 
# ------------------------------------------------------------------------

def DelPromethues(key):
    global GaugeINT
    Mkey = MID + '_' + key
    if Mkey in GaugeINT:
        GaugeW1.pop(key)

def UpdPromethues(key,val):
    global GaugeINT
    Mkey = MID + '_' + key
    if not isSetPromethues(key):
        AddPromethues(key)
    if Mkey in GaugeINT:
        # print('UPD'+Mkey+'-'+str(val))
        GaugeINT[Mkey].set(val)

def AddPromethues(key):
    global GaugeINT
    Mkey = MID + '_' + key
    if  key not in GaugeINT:
        GaugeINT[Mkey]=Gauge(Mkey,key)
            
def POLLEDgauge(key):
    SendMSG('Polled Gauge '+str(key))
    
def isSetPromethues(key):
    Mkey = MID + '_' + key
    if Mkey not in GaugeINT:
        return False
    else:
        return True

# ------------------------------------------------------------------------
#   Intial Parm Load and validation
# ------------------------------------------------------------------------

def ValidatePARMS():
    global MID
    global PortNo
    global POLLgap

    configPOLL.read('POLL.ini')
    configPINS.read('PINS.ini')

    if "location" not in configPOLL["POLL"]:
        SendMSG('location missing from Config - Job Terminated')
        return True
    if "name" not in configPOLL["POLL"]:
        SendMSG('name missing from Config - Job Terminated')
        return True

    print("Location     : ",configPOLL["POLL"]["location"])
    print("Name         : ",configPOLL["POLL"]["name"])
    SendMSG(configPOLL["POLL"]["name"]+' / '+configPOLL["POLL"]["name"])
    MID=configPOLL["POLL"]["location"]+'_'+configPOLL["POLL"]["name"]+'_V2'
    SendMSG('Promethues Prefix : '+MID)

    PortNo=8010
    if "port" in configPOLL["POLL"]: 
        PortNo=int(configPOLL['POLL']['port'])

    POLLgap=30
    if "Time" in configPOLL["POLL"]:
        POLLgap=int(configPOLL['POLL']['Time'])

    SendMSG('Poll Intervals : '+str(POLLgap)+' Seconds')
    SETpins()
    return False

# --------------------------------------------------------------------------

def SendMSG(msg):
    print(msg)
    #journal.send(msg)  

# ---------------------------------------------------------------------------
#   API Server : Open API server to Port 18100
# ---------------------------------------------------------------------------

class gpioHTTPServer_RequestHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):         
        self.send_response(200)      
        self.send_header('Access-Control-Allow-Origin', '*')                
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With") 

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type','text/plain')
        self.end_headers()
        Rsn=APIincoming(self.path)   
        self.wfile.write(bytes(Rsn, "utf8"))

    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(bytes("OK","utf8"))

# -----------------------------------------------------------------------
#    Incoming API handler 
# -----------------------------------------------------------------------

def APIincoming(url):
    qsp=dict(parse.parse_qsl(parse.urlsplit(url).query))
    #print(qsp)
    if 'API' in qsp:
        if qsp['API']!='A4C3D2E5112':
           return 'Security Volation'
        RtnTxt=''
    else:
        return 'Security Key Missing'

    if 'TYP' in qsp:
        if qsp['TYP']=='RLY':
            return apiRELAY(qsp)
        return 'Support Types (RLY,SWT,MON)'
    else:
        return 'Missing Task'

def apiRELAY(qsp):

    # Toggle Relay
    if 'PID' in qsp:
        if qsp['PID'] in configPINS:
            return RelayTOGGLE(qsp['PID'])

    # Return All Relay Status
    RtnTxt=''
    for pin in configPINS:
        if pin != 'DEFAULT':
            if configPINS[pin]["Type"]=='Relay':
                if RelayGET(pin)==0:
                    RlyStat='OFF'
                else:
                    RlyStat='ON'                    
                RtnTxt=RtnTxt+str(pin)+'('+configPINS[pin]['NAME']+')='+RlyStat+'  '

    return RtnTxt   
   
# ---------------------------------------------------------------------------

def main():
    SendMSG('Version '+Vers)
    if ValidatePARMS(): return

# Start Promethus Server
    start_http_server(PortNo)
    SendMSG('Prometheus running on '+str(PortNo))

# Start API Server 
    server_address = ('', 18100)
    httpd = HTTPServer(server_address, gpioHTTPServer_RequestHandler)
    httpd.socket.settimeout(1)
    httpd.handle_request()
    SendMSG('GPIO API running on 18100')

# Main Loop
    while KillSwitch:
        SIDs={}                      # Activate Sensors
        SIDs=LISTwire1()             # Wire-1 Sensor Controls
        print('SID:',SIDs)

        PNs=PINpoll()                # Pin Poll 
        print('PINS:',PNs)
        SIDs = {**SIDs, **PNs}   

        if 'ZIGBEE' in configPOLL:   # ZigBee Poll
            ZBs=ZBpoll()
            print('ZBs:',ZBs)
            SIDs = {**SIDs, **ZBs}   

        for ActSid in GaugeINT:      # Remove Dead Sensors
            if ActSid not in SIDs:
                DelPromethues(ActSid)

        for sid in SIDs:             # Add New Sensors
            if not isSetPromethues(sid):
                AddPromethues(sid)

        for sid in SIDs:             # Update Sensors
            UpdPromethues(sid,SIDs[sid])

        GapCnt=0
        while GapCnt <= POLLgap:
            time.sleep(1)
            httpd.handle_request()   # Poll API Getway
            GapCnt+=1

    sys.stdout.flush()  

if __name__=="__main__":
    main()
