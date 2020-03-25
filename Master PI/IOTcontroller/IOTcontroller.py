#!/usr/bin python3

# ----------------------------------------------------------------------------
#  IOTcontroller
#    Little Program to Contract 2 extractor fans via relays based on 3 DHT22
#    sensors.  
#    DB is used to montior the effectiveness of the fans and help fine
#    tune the settings over time.  Postgres is the DB of choice here 
#
#    APIrest to get/set controllers settings
#    
#    Additional code to montior the router to see if anyone is home. 
#    This was to expand this later into an alarm aswell with z-wave modules
#    .... maybe
#
#    Parm : CONTROL.ini
#
#    V 0.0.1 - Mar 2002 - Initial coding 
#  
# ----------------------------------------------------------------------------

from http.server import BaseHTTPRequestHandler, HTTPServer
from pynetgear import Netgear
import requests
from gpiozero import LED, Button

from urllib import parse
from gpiozero import LED

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

#Wire One Directory
Ddir='/sys/bus/w1/devices/'
cntlINI = configparser.ConfigParser()

# 4 Port Relay Pins 
Extractor1 = 0
Extractor2 = 0
Lights = 0
Alarm = 0

#Bedroom1, Bedroom2, Bathroom
Sensors=[0,0,0]

TEMPtrig=21
HUMtrig=80

ButtonOV = 0
Router = False
PollGAP = 10   # Poll Gap between checking sensors

ActDEV=[]
PrvDEV=[]

#KillSwitch = True
#POLLlst={"DEF":0}
#GaugeW1={"DEF":20}   # W1 Sensors
#GaugePIN={"DEF":20}  # Activate Pins
#Vers='1.1.0'
#MID='XX'

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
    
    if "netgear" in cntlINI["SETTINGS"]:
        SendMSG("NetGear Active")
        netgear = Netgear(password=cntlINI["SETTINGS"]["netgear"])   
        if 'OWNER' in cntlINI:
            Router=True
            for sfld in cntlINI["OWNER"]:
                print(cntlINI["OWNER"][sfld])

    if "Fan1" in cntlINI["SETTINGS"]:
        Extractor1=LED(cntlINI["SETTINGS"]["Fan1"]) 
        SendMSG("Extractor 1 on Pin "+cntlINI["SETTINGS"]["fan1"])
    else:
        SendMSG("WARNING : No Fan1 Sensors Set")

    if "Fan2" in cntlINI["SETTINGS"]:
        Extractor2=LED(cntlINI["SETTINGS"]["Fan2"])
        SendMSG("Extractor 2 on Pin "+cntlINI["SETTINGS"]["fan2"])
    else:
        SendMSG("WARNING : No Fan2 Sensors Set")

    if "Lights" in cntlINI["SETTINGS"]:
        ExtLights=LED(cntlINI["SETTINGS"]["Lights"])
        SendMSG("External Lights on Pin "+cntlINI["SETTINGS"]["Lights"])

    if "Alarm" in cntlINI["SETTINGS"]:
        Alarm=LED(cntlINI["SETTINGS"]["Alarm"])
        SendMSG("Alarm on Pin "+cntlINI["SETTINGS"]["Alarm"])

    if "Button" in cntlINI["SETTINGS"]:
        ButtonOV=Button(cntlINI["SETTINGS"]["Button"])
        SendMSG("Button on Pin "+cntlINI["SETTINGS"]["Button"])

    if "Bedroom1" in cntlINI["SETTINGS"]:
        Sensors[0]=cntlINI["SETTINGS"]["Bedroom1"]
        SendMSG("BedRoom1 Sensor on Pin "+cntlINI["SETTINGS"]["Bedroom1"])
    if "Bedroom2" in cntlINI["SETTINGS"]:
        Sensors[1]=cntlINI["SETTINGS"]["Bedroom2"]
        SendMSG("BedRoom2 Sensor on Pin "+cntlINI["SETTINGS"]["Bedroom2"])
    if "Bathroom" in cntlINI["SETTINGS"]:
        Sensors[2]=cntlINI["SETTINGS"]["Bathroom"]
        SendMSG("Bathroom Sensor on Pin "+cntlINI["SETTINGS"]["Bathroom"])
        
    if Sensors[0] == 0 and Sensors[1] == 0:
        SendMSG("WARNING : No BedRoom Sensors Set")
    if Sensors[2] == 0 :
        SendMSG("WARNING : No Bathroom Sensors Set")


    TEMPtrig=21
    HUMtrig=80
    if "TEMPtrig" in cntlINI["SETTINGS"]:
        TEMPtrig=cntlINI["SETTINGS"]["TEMPtrig"]
    SendMSG("Temp Trigger "+str(TEMPtrig))

    if "HUMtrig" in cntlINI["SETTINGS"]:
        HUMtrig=cntlINI["SETTINGS"]["HUMtrig"]
    SendMSG("Hum Trigger "+str(HUMtrig)) 
    PollGAP=30
    if "Poll" in cntlINI["SETTINGS"]:
        PollGAP=int(cntlINI["SETTINGS"]["Poll"])
    SendMSG("Poll Gap "+str(PollGAP)+" Seconds")

    return False

# --------------------------------------------------------------------------

def SendMSG(msg):
    print(msg)
    #journal.send(msg)  

# ---------------------------------------------------------------------------
#   API Server : Open API server to Port 18100
# ---------------------------------------------------------------------------

class gpioHTTPServer_RequestHandler(BaseHTTPRequestHandler):
    #def do_OPTIONS(self):         
    #    self.send_response(200)      
        #self.send_header('Access-Control-Allow-Origin', '*')                
        #self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    #    self.send_header('Access-Control-Allow-Methods', 'GET, POST')
        #self.send_header("Access-Control-Allow-Headers", "X-Requested-With") 
    #    return

    def do_GET(self):
        SendMSG('------------------------------ GET')
        self.send_response(200)
        self.send_header('Content-type','text/plain')
        self.end_headers()
        Rsn=APIincoming(self)   
        self.wfile.write(bytes(Rsn, "utf8"))
        SendMSG('------------------------------ GET (END)')
        return

    def do_POST(self):
        SendMSG('------------------------------ POST')
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(bytes("OK","utf8"))
        return

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


def APIincoming(self):
    print(self.path)
    print('----')
    pp=self.path.split('/')
    print(pp)
    print('----')
    LOGmsgs('A001','M',self.address_string()+':'+self.path+':'+self.command)

    if 'CANDY' not in pp:
        LOGmsgs('0001','S','Security Key Invalid')
        return 'Security Volation'

    if 'TYP' in qsp:
        if qsp['TYP']=='RLY':
            return apiRELAY(qsp)

        return 'Support Types (RLY,SWT,MON)'
    else:
        return 'Missing Task'

# WirePush notifications

def OwnerHome(nam):
    r = requests.get('https://wirepusher.com/send?id=T27mmpnGY&title=Home&message='+nam+' Home&type=NewDevice&message_id=1')
    r.status_code
    #SendMSG(r)
def ClearMSG():
    r = requests.get('https://wirepusher.com/send?id=T27mmpnGY&type=wirepusher_clear_notification&message_id=1')
    r.status_code
    #SendMSG(r)

def CheckSENSORS():
    localtime = time.asctime( time.localtime(time.time()) )

    if Sensors[0]:   #  Bedroom1
        humidity1,temperature1 = Adafruit_DHT.read_retry(22, Sensors[0])
    if Sensors[1]:   #  Bedroom2
        humidity2,temperature2 = Adafruit_DHT.read_retry(22, Sensors[1])
    
    if  Extractor1.value:
        if humidity1 > 0 and humidity1 < HUMtrig-5:
            Extractor1.off
        if humidity2 > 0 and humidity2 < HUMtrig-5:
            Extractor1.off
        if temperature1 > 0 and temperature1 < TEMPtrig-2:
            Extractor1.off
        if temperature2 > 0 and temperature2 < TEMPtrig-2:
            Extractor1.off
    else:
        if humidity1 > 0 and humidity1 > HUMtrig+5:
            Extractor1.on
        if humidity2 > 0 and humidity2 > HUMtrig+5:
            Extractor1.on
        if temperature1 > 0 and temperature1 > TEMPtrig+2:
            Extractor1.on
        if temperature2 > 0 and temperature2 > TEMPtrig+2:
            Extractor1.on

    LOGvalues("Bedroom1",humidity1,temperature1,Extractor1.value)
    LOGvalues("Bedroom2",humidity2,temperature2,Extractor1.value)

    if Sensors[2]:   #  Bathroom
        humidity3,temperature3 = Adafruit_DHT.read_retry(22, Sensors[2])
    if  Extractor2.value:
        if humidity3 > 0 and humidity3 < TEMPtrig:
            Extractor2.off
    else:
        if humidity3 > 0 and humidity3 > TEMPtrig+5:
            Extractor2.on

    LOGvalues("Bathroom",humidity3,temperature3,Extractor2.value)

def CheckROUTER():
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

def LOGvalues(SID,HUM,TMP,STA):
    SendMSG(SID+' : H/'+str(HUM)+' T/'+str(TMP)+' : '+str(STA))
def LOGmsgs(trc,typ,msg):
    SendMSG(trc+':'+typ+'-'+msg)

   # ---------------------------------------------------------------------------

def main():
    ValidatePARMS()   #  Load in control Parms

    # Start API Server 
    server_address = ('', 18101)
    httpd = HTTPServer(server_address, gpioHTTPServer_RequestHandler)
    httpd.socket.settimeout(1)
    httpd.handle_request()
    SendMSG('IOTcontroller API running on 18101')

    while 1:
        #CheckSENSORS()
        #if Router:
        #    CheckROUTER()

        GapCnt=0
        while GapCnt <= PollGAP:
            httpd.handle_request() # Poll API Getway
            if ButtonOV:
                Button.wait_for_press(1) 
            else:
                time.sleep(1)
            GapCnt+=1

if __name__=="__main__":
    main()
