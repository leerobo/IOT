#!/usr/bin python3

# ----------------------------------------------------------------------------
#  IOTcontroller
#     Use IO to control Relays, Alerts and general settings 
#    
#    To Set : View Readme.txt in folder
#
#    V 0.1.0  -  2020 Mar - add PYNETGEAR 
#  
# ----------------------------------------------------------------------------

from http.server import BaseHTTPRequestHandler, HTTPServer
from pynetgear import Netgear
import requests

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
cntlINI = configparser.ConfigParser()

KillSwitch = True
POLLlst={"DEF":0}
GaugeW1={"DEF":20}   # W1 Sensors
GaugePIN={"DEF":20}  # Activate Pins
Vers='1.1.0'
MID='XX'

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





# ------------------------------------------------------------------------
#   Intial Parm Load and validation
# ------------------------------------------------------------------------

def ValidatePARMS():
    cntlINI.read('CONTROL.ini')
    for fld in cntlINI:
        print(fld)
        for sfld in cntlINI[fld]:
            print(cntlINI[fld][sfld])
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


# ----------------------------------------------------------------------
#  API CALLS
# ----------------------------------------------------------------------

def APIsensors():
    params = {"words": 10, "paragraphs": 1, "format": "json"}
    response = requests.get(f"http://192.168.2.2/api/236FAB4DA9/sensors/")
    print (type(response.json()))
    print(response.json())

    for song in response.json():   
        print(song)
        for song2 in song:  
            print(song2)

# ----------------------------------------------------------------------
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
    if 'RLY' in qsp:
        if qsp['TYP'] in configPINS:
            return RelayTOGGLE(qsp['TYP'])

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

def OwnerHome(nam):
    r = requests.get('https://wirepusher.com/send?id=T27mmpnGY&title=Home&message='+nam+' Home&type=NewDevice&message_id=1')
    r.status_code
    #SendMSG(r)
def ClearMSG():
    r = requests.get('https://wirepusher.com/send?id=T27mmpnGY&type=wirepusher_clear_notification&message_id=1')
    r.status_code
    #SendMSG(r)

   
# ---------------------------------------------------------------------------

def main():
    APIsensors()
    ValidatePARMS()
    netgear = Netgear(password='1970terry')  # Logon 
    
    ActDEV=[]
    PrvDEV=[]
    APIsensors()

    while 1:
        PrvDEV=ActDEV[:]
        ActDEV.clear()
        localtime = time.asctime( time.localtime(time.time()) )
        for i in netgear.get_attached_devices():
            if i.type == 'wireless':
                ActDEV.append(i.mac)
                if i.mac not in PrvDEV:
                    for own in cntlINI['OWNER']:
                        dets=cntlINI['OWNER'][own].split('#')
                        if i.mac == dets[1]:
                            SendMSG(localtime+': '+dets[0]+" is Home - "+i.name+' ('+i.mac+')')
                            OwnerHome(dets[0])
                        #else:
                            #SendMSG("New Device  :  "+i.name+' ('+i.mac+')')

                #if i.mac in PrvDEV:
                    #SendMSG("Found Device  :  "+i.name+' ('+i.mac+')')
            #SendMSG(i.name+' / '+i.ip+' / '+i.mac+' / '+i.type) 

        for mm in PrvDEV:
            if mm not in ActDEV:
                SendMSG(localtime+": Lost Device  :  "+mm)
        time.sleep(30)
        # Clear Phone
        ClearMSG()
        

if __name__=="__main__":
    main()
