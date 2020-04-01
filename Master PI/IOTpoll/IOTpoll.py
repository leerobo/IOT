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

from http.server import BaseHTTPRequestHandler, HTTPServer
from prometheus_client import start_http_server, Gauge

from urllib import parse
import RPi.GPIO as GPIO
import configparser 
import time
import http.client
import json
import ZigBee as ZB

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
import requests

Ddir='/sys/bus/w1/devices/'
configPOLL = configparser.ConfigParser()
configPINS = configparser.ConfigParser()
KillSwitch = True
POLLlst={"DEF":0}
GaugeW1={"DEF":20}   # W1 Sensors
GaugePIN={"DEF":20}  # Activate Pins
Vers='1.1.0'
MID='XX'
ZBc = ZB

# -----------------------------------------------------------------
#    Wire-1 : Wire 1 functions and routines 
# -----------------------------------------------------------------

def LISTwire1(SIDs):
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
    if 'ZIGBEE' not in configPOLL: return False
    params = {"words": 10, "paragraphs": 1, "format": "json"}
    response = requests.get(f"http://"+configPOLL["ZIGBEE"]["ip"]+"/api/"+configPOLL["ZIGBEE"]["key"]+"/sensors/")
    if response.status_code != 200:
        print("ZigBee Return Error : "+str(response.status_code))
        return True
    ZB.ZBsensors(response.json())   #  Store Sensors in ZigBee Class

# -----------------------------------------------------------------
#   Relays : Controllers for Relays
# -----------------------------------------------------------------

# Return Pin ON/OFF status
def RelayGET(PIN):
    if GPIO.input(int(PIN)):
        return 1  
    else:
        return 0   
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

# -------------------------------------------------------------------
#  PIN Setup : Setup Pins settings
# -------------------------------------------------------------------

def SETpins():
    GPIO.setwarnings(False) 
    GPIO.setmode(GPIO.BCM)

    for pin in configPINS:
        if pin != 'DEFAULT':
            if configPINS[pin]["Type"]=='Relay':
                SendMSG('TYPE:RELAY'+'-'+str(pin)+' '+configPINS[pin]['NAME']+' Initialised')
                GPIO.setup(int(pin), GPIO.OUT)
                GPIO.output(int(pin), GPIO.HIGH)

            if configPINS[pin]["Type"]=='AM2302' or  configPINS[pin]["Type"]=='DHT22':
                SendMSG('TYPE:HUM/TEMP'+'-'+str(pin)+' '+configPINS[pin]['NAME'])

            if configPINS[pin]["Type"]=='Switch':
                SendMSG('TYPE:SWITCH'+'-'+str(pin)+' '+configPINS[pin]['NAME']+' Initialised')
                GPIO.setup(int(pin), GPIO.IN, pull_up_down=GPIO.PUD_UP)

            if configPINS[pin]["Type"]=='Motion':
                SendMSG('TYPE:Motion'+'-'+str(pin)+' '+configPINS[pin]['NAME']+' Initialised')
                GPIO.setup(int(pin), GPIO.IN, pull_up_down=GPIO.PUD_UP)
             
    #sys.stdout.flush()  

# ------------------------------------------------------------------------
#   Promethues : Comms to Promethus Server 
# ------------------------------------------------------------------------

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
    if typ=='W1' and key in GaugeW1:
        GaugeW1[key].set(val)
    elif  typ=='PIN' and key in GaugePIN:
        SendMSG('UPD '+typ+' PIN : '+key+'  VAL : '+str(val))
        GaugePIN[key].set(val)

def AddPromethues(typ,key):
    global GaugePIN
    global GaugeW1
    Mkey = MID + '_' + key
    SendMSG('ADD:'+Mkey+' - '+typ+' - '+key)
    if  typ == 'W1' and not key in GaugeW1:
        GaugeW1[key]=Gauge(Mkey,key)
        GaugeW1[key].set_function(POLLEDgauge,key)
    elif typ == 'PIN' and not key in GaugePIN:
        GaugePIN[key]=Gauge(Mkey,key)
        # GaugePIN[key].set_function(POLLEDgauge,key)
            
def POLLEDgauge(key):
    SendMSG('Polled Gauge '+str(key))
    
def isSetPromethues(typ,key):
    Mkey = MID + '_' + key
    if typ == 'W1' and not key in GaugeW1:
        return False
    elif typ == 'PIN' and not key in GaugePIN:
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
    global GaugeW1
    SendMSG('Version '+Vers)
    if ValidatePARMS(): return
    if ZBsetup(): return

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
        SIDs=[]    
        SIDs=LISTwire1(SIDs)       # Wire-1 Sensor Controls

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

                elif configPINS[Pin]["Type"]=='Relay':
                    UpdPromethues('PIN','RELAY_'+Pin,RelayGET(Pin) )

                elif configPINS[Pin]["Type"]=='Switch':
                    UpdPromethues('PIN','SWITCH_'+Pin,RelayGET(Pin) )

                elif configPINS[Pin]["Type"]=='Motion':
                    UpdPromethues('PIN','MOTION_'+Pin,RelayGET(Pin) )
                else:
                    SendMSG("Pin Unknown Type : "+configPINS[Pin]["Type"])

        
            

        GapCnt=0
        SendMSG("Polled Internally")
        while GapCnt <= POLLgap:
            time.sleep(1)
            httpd.handle_request() # Poll API Getway
            GapCnt+=1


    sys.stdout.flush()  

if __name__=="__main__":
    main()
