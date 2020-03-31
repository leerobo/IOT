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
#    V 0.0.1 - Mar 2020 - Initial coding 
#    V 0.0.2 - Apr 2020 - Add support for ZigBee deconz REST api
#  
# ----------------------------------------------------------------------------

from http.server import BaseHTTPRequestHandler, HTTPServer
from pynetgear import Netgear
import requests
from gpiozero import LED, Button

import websocket
try:
    import thread
except ImportError:
    import _thread as thread
import time

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

cntlINI = configparser.ConfigParser()
cntlGPIO = configparser.ConfigParser()

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
Vers='0.2.0'
#MID='XX'


# -----------------------------------------------------------------
#   Class objects 
# -----------------------------------------------------------------

class ZBsensors:
    # Store Sensors available to ZigBee and routines to extract/update info
    def __init__(self, ZBids):
        self.SIDX={}
        self.SID={}
        for sid in ZBids:
            print(sid)
            print(ZBids[sid])

        for sid in ZBids:
            self.SIDX[sid]=ZBids[sid]['etag']
            etag=ZBids[sid]['etag']

            if etag not in self.SID:
                print(ZBids[sid]['name']+' Sensor Found')
                self.SID[etag]={}
                self.SID[etag]['name']=ZBids[sid]['name']
                self.SID[etag]['modelid']=ZBids[sid]['modelid']

                if ZBids[sid]['modelid'] == 'lumi.remote.b1acn01':
                    self.SID[etag]['type']='Button'
                elif ZBids[sid]['modelid'] == 'lumi.weather':
                    self.SID[etag]['type']='MultiSensor'
                elif ZBids[sid]['modelid'] == 'lumi.sensor_magnet.aq2':
                    self.SID[etag]['type']='MagSwitch'
                elif ZBids[sid]['modelid'] == 'PHDL00':
                    self.SID[etag]['type']='Controller'
                else:
                    self.SID[etag]['type']='N/A'                    

            if 'config' in ZBids[sid]:    
                if 'battery' in ZBids[sid]['config']:
                    self.SID[etag]['battery']=ZBids[sid]['config']['battery']
                if 'temperature' in ZBids[sid]['config']:
                    self.SID[etag]['temp']=ZBids[sid]['config']['temperature']

            if 'state' in ZBids[sid]:
                if 'temperature' in ZBids[sid]['state']:
                    self.SID[etag]['temp']=ZBids[sid]['state']['temperature']                    
                if 'humidity' in ZBids[sid]['state']:
                    self.SID[etag]['hum']=ZBids[sid]['state']['humidity']                    
                if 'pressure' in ZBids[sid]['state']:
                    self.SID[etag]['Pres']=ZBids[sid]['state']['pressure']                    
                if 'open' in ZBids[sid]['state']:
                    self.SID[etag]['open']=ZBids[sid]['state']['open']
                if 'lastupdated' in ZBids[sid]['state']:
                    self.SID[etag]['lastupdated']=ZBids[sid]['state']['lastupdated']

        for sid in self.SID:
            print(self.SID[sid])
        for sid in self.SIDX:
            print(sid+':'+self.SIDX[sid])

        self.ids = ZBids   #  Json DICT

    #def ZBGetID(self,ZBid):
    #    return self.ids[ZBid]

#  '2': {'config': {'battery': 100, 'offset': 0, 'on': True, 'reachable': True}, 
#  'ep': 1, 
#  'etag': '1a8a05aef7eef79babaf83bcddceb3c0', 
#  'manufacturername': 'LUMI',
#  'modelid': 'lumi.weather',
#  'name': 'Basement', 
#  'state': {'lastupdated': '2020-03-28T10:06:25', 'temperature': 1623}, 
#  'swversion': '20191205',
#  'type': 'ZHATemperature',
#  'uniqueid': '00:15:8d:00:04:5c:6f:7d-01-0402'}, 
    def GetTYPE(self,ZBid):
        Etag=self.SIDX[ZBid]
        return self.SID[Etag]['type']
    def GetNAME(self,ZBid):
        Etag=self.SIDX[ZBid]
        return self.SID[Etag]['name']
    def GetSENSOR(self,ZBid):
        Etag=self.SIDX[ZBid]
        return self.SID[Etag] 

    def Update(self,ZBsid):
        if 'config' in ZBsid:
            print(self.ids[ZBsid['id']]['config'])
            print(ZBsid['id']['config'])
            self.ids[ZBsid['id']]['config'] =ZBsid['id']['config']
        if 'state' in ZBsid:
            self.ids[ZBsid['id']]['state'] =ZBsid['id']['state']
               
    def CheckBATTERY(self):
        prvEid=' '
        for sid in self.ids:
            if 'battery' in self.ids[sid]['config'] and prvEid != self.ids[sid]['etag'] :
                if self.ids[sid]['config']['battery'] != None:
                    if int(self.ids[sid]['config']['battery']) < 40 :
                        prvEid=self.ids[sid]['etag']
                        Alert("Battery",self.ids[sid]['name']+' Sensor  battery @ '+str(self.ids[sid]['config']['battery'])+'%  ['+prvEid+']' )
        
class GPIOpins:
    # store the GPIO.ini here and allocate GPIO methods here 
    def __init__(self, GPIOs):
        self.pins = {}
        for section in GPIOs.sections():
            self.pins[section] = {}
            for key, val in GPIOs.items(section):
                self.pins[section][key] = val.lower()
        for pin in self.pins:
            if self.pins[pin]['type']=='relay':
                LED(pin).off()
                print('pin '+str(pin)+' set to relay')

    def ON(self, id):
        for pin in self.pins:
            if self.pins[pin]['id']==id.lower():
                LED(pin).on(pin)

    def OFF(self, id):
        for pin in self.pins:
            if self.pins[pin]['id']==id.lower():
                LED(pin).off(pin)

    def TOGGLEbyID(self, id):
        for pin in self.pins:
            if self.pins[pin]['id']==id.lower():
                return self.TOGGLEbyPIN(pin)

    def TOGGLEbyPIN(self,pin):
        if self.pins[pin]['type'] == 'relay':
            LED(pin).toggle()
            print('Pin '+str(pin)+' Toggled')
            return LED(pin).value
        print('Not supported yet - '+self.pins[pin]['type'] )
        return -1

# ------------------------------------------------------------------------
#   Intial Parm Load and validation
# ------------------------------------------------------------------------

def ValidatePARMS():
    global GPIOpinsC
    cntlINI.read('CONTROL.ini')  # Controllers
    cntlGPIO.read('GPIO.ini')    # GPIO settings
    
    # If netgear set allow access to Netgear Router
    if "netgear" in cntlINI["SETTINGS"]:
        SendMSG("NetGear Active")
        netgear = Netgear(password=cntlINI["SETTINGS"]["netgear"])   
        if 'OWNER' in cntlINI:
            Router=True
            for sfld in cntlINI["OWNER"]:
                print(cntlINI["OWNER"][sfld])

    # ZigBee controllers
    if cntlINI["ZIGBEE"]["key"] == '':
        SendMSG("ZigBee Key Missing ")
        return True
    SendMSG("ZigBee "+str(cntlINI["ZIGBEE"]["ip"])+" : "+str(cntlINI["ZIGBEE"]["key"] ))
    GPIOpinsC=GPIOpins(cntlGPIO)

    return False

# --------------------------------------------------------------------------

def SendMSG(msg):
    print(msg)
    #journal.send(msg)  

def Alert(lvl,msg):
    print('Alert('+lvl+') '+msg)
    r = requests.get('https://wirepusher.com/send?id=dzk6mpnEN&title=Home&message='+msg+'&type='+lvl+'&message_id=1')
    r.status_code

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
        ftrTXT=open('Footer.html','r+')
        pageTYP,Rsn=APIincoming(self)

        self.send_response(200)
        if pageTYP=='JSON':
            self.send_header('application/json')
            Rply = Rsn
        else:
            self.send_header('Content-type','text/html')
            hdrTXT=open('Header.html','r+')
            Rply = hdrTXT.read()+Rsn+ftrTXT.read()

        self.end_headers()
        self.wfile.write(bytes(Rply, "utf8"))
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

def ZBsetup():
    global ZBconfig, ZBsensors, ZBsensorC
    params = {"words": 10, "paragraphs": 1, "format": "json"}
    response = requests.get(f"http://"+cntlINI["ZIGBEE"]["ip"]+"/api/"+cntlINI["ZIGBEE"]["key"]+"/sensors/")
    if response.status_code != 200:
        print("ZigBee Return Error : "+str(response.status_code))
        return True
    ZBSensors=response.json()
    print("ZigBee Sensors Set")
    ZBsensorC = ZBsensors(response.json())  #  Store Sensors
    ZBsensorC.CheckBATTERY()                #  Check Batterys

    params = {"words": 10, "paragraphs": 1, "format": "json"}
    response = requests.get(f"http://"+cntlINI["ZIGBEE"]["ip"]+"/api/"+cntlINI["ZIGBEE"]["key"]+"/config")
    if response.status_code != 200:
        print("ZigBee Return Error : "+str(response.status_code))
        return True
    ZBconfig=response.json()
    print("ZigBee Config Set")

def ZBchange(msg):
    jmsg=json.loads(msg)
    if 'id' not in jmsg:
        print('----Unknown Sensor Change Ignored------')
        print(msg)
        return
    IOTcntl(jmsg)  #  Core Processing 

# ----------------------------------------------------------------------
#   ZigBee DeCONz WebSocket Setup
# ----------------------------------------------------------------------

def WBws_message(ws, message):
    ZBchange(message)

def WBws_error(ws, error):
    print(error)

def WBws_close(ws):
    print("### closed ###")

def WBws_open(ws):
    def run(*args):
        for i in range(3):
            time.sleep(1)
            ws.send("Hello %d" % i)
        time.sleep(1)
        ws.close()
        print("thread terminating...")
    thread.start_new_thread(run, ())

# ----------------------------------------------------------------------
#   Decode the URL into simple Array and Dict of parms
# ----------------------------------------------------------------------

def DecodeURL(URLtxt):
    Ux= URLtxt.split('?')
    UParms = {}
    Uarr=()
    print(URLtxt)

    if Ux[0] == '/':  #No Url no Parms (Index)
        return Uarr,UParms

    if len(Ux) > 0:
        if Ux[0][0:1] == '/':
            Uarr=Ux[0].split('/')
            print(Uarr)

    if len(Ux) == 2 or len(Ux) == 1 and Ux[0][0:1] != '/':
        if len(Ux) == 2 :
            Uprm=Ux[1].split('&')
        else:
            Uprm=Ux[0].split('&')
        for Uprms in Uprm:
            print(Uprms)
            Upp=Uprms.split('=')
            UParms[Upp[0]]=Upp[1]
        
    return Uarr,UParms

# ----------------------------------------------------------------------
#    Incoming API handler 
# -----------------------------------------------------------------------

def APIincoming(self):
    LOGmsgs('A001','M',self.address_string()+':'+self.path+':'+self.command)
    URLlvl,URLparm = DecodeURL(self.path)

    if len(URLlvl) == 0:   # Return Index if requried here 
        bdyTXT=open('bdyTXT.html','r+')
        return 'HTML',bdyTXT.read()

    # Place here different URLlvl 
    return 'HTML','<body><hdr>Missing Task</hdr></body>'

# WirePush notifications

def WirePush(Msg,Typ):
    r = requests.get('https://wirepusher.com/send?id=dzk6mpnEN&title=Home&message='+Msg+'&type='+Typ+'&message_id=1')
    r.status_code
def ClearMSG():
    r = requests.get('https://wirepusher.com/send?id=dzk6mpnEn&type=wirepusher_clear_notification&message_id=1')
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

# ------------------------------------------------------------------------------
#   Core processing Based on Sensors 
# ------------------------------------------------------------------------------

def IOTprintMSG(Sid):
    SidID=Sid['id']
    Prtlne = str(SidID)
    Prtlne=Prtlne+'-'+ZBsensorC.GetTYPE(SidID)
    Prtlne=Prtlne+':'+ZBsensorC.GetNAME(SidID)

    if 'state' in Sid:
        PrtLne=Prtlne+'*STATE*'
        if 'temperature' in Sid['state']:
            Prtlne=Prtlne+' (Temp:'+str(float(Sid['state']['temperature']/100))+') '
        if 'humidity' in Sid['state']:
            Prtlne=Prtlne+' (Hum:'+str(float(Sid['state']['humidity']/100))+'%) '
        if 'pressure' in Sid['state']:
            Prtlne=Prtlne+' (Pres:'+str(Sid['state']['pressure'])+') '
        if 'open' in Sid['state']:
            if Sid['state']['open']==True:
                Prtlne=Prtlne+' Door:Open'
            else:
                Prtlne=Prtlne+' Door:Closed'

    if 'config' in Sid:
        PrtLne=Prtlne+'*CONFIG*'
        if 'battery' in Sid['config']:
            Prtlne = Prtlne+' (Bat:'+str(Sid['config']['battery'])+'%)'

    return Prtlne  

def IOTcntl(Sid):
    print('----Event--------------------------------------------------------')
    print(Sid)
    print(IOTprintMSG(Sid))
    print('-----------------------------------------------------------------')

    SidID=Sid['id']
    # ----------------------- Sensors Config Change
    if 'config' in Sid:
        if 'battery' in Sid['id']['config']:
            if Sid['id']['config']['battery'] < 20:
                Alert('Battery','Low Battery in '+ZBsensorC.GetNAME[SidID]+' Sensor')
            if Sid['id']['config']['battery'] < 5:
                Alert('Battery','Replace Battery in '+ZBsensorC.GetNAME[SidID]+' Sensor')
        #ZBsensorC.Update(Sid)
        return

    #   Button - Toggle Bedroom Fan
    if  ZBsensorC.GetTYPE(SidID)=='Button':
        print('Button Pressed '+str(Sid['state']['buttonevent']))
        if Sid['state']['buttonevent']==1002 or Sid['state']['buttonevent'] == 1003: # Button pressed
            GPIOpinsC.TOGGLEbyID('bedroom')
        elif Sid['state']['buttonevent']==1004:     # Button double pressed
            GPIOpinsC.TOGGLEbyID('bathroom')
        return
    
    # if  ZBsensorC.GetTYPE(SidID)=='MultiSensor':
    #     print('Humidity '+str(int(Sid['state']['humidity']/100))+' on '+ZBsensorC.GetNAME(SidID))
    #     if Sid['state']['humidity'] >= 7500 and ZBsensorC.GetNAME(SidID)=='bathroom':
    #         GPIOpinsC.ON('bathroom')
    #     if Sid['state']['humidity'] <= 7000 and ZBsensorC.GetNAME(SidID)=='bathroom':
    #         GPIOpinsC.OFF('bathroom')
    #     if Sid['state']['humidity'] >= 6500 and ZBsensorC.GetNAME(SidID)=='bedroom': 
    #         GPIOpinsC.ON('bedroom')
    #     if Sid['state']['humidity'] <= 5000 and ZBsensorC.GetNAME(SidID)=='bedroom': 
    #         GPIOpinsC.OFF('bedroom')
    #     return

    if  ZBsensorC.GetTYPE(SidID)=='MagSwitch':
        print(Sid)
        if 'open' in Sid['id']['state']:
            if 'open' in Sid['id']['open']==True:
                Alert('Door',ZBsensorC.GetNAME(SidID)+' Open')
        return

    if  ZBsensorC.GetTYPE(SidID)=='ZHATemperature':
        return

    if  ZBsensorC.GetTYPE(SidID)=='ZHAPressure':
        return

    print('-----------------------------------------------------')
    print(ZBsensorC.GetTYPE(SidID)+': Unsupport / Ignored')
    print(Sid)
    print('   +    +   +   +   +   +   +   +   +   +   +   +   +')
    print(ZBsensorC.GetSENSOR(SidID))
    print('-----------------------------------------------------')

   # ---------------------------------------------------------------------------

def main():
    print('Version : '+Vers)
    if ValidatePARMS():   #  Load in control Parms
        return
    if ZBsetup():         #  Setup deConz ZigBee
        return 

    # Start API Server 
    server_address = ('', 18101)
    httpd = HTTPServer(server_address, gpioHTTPServer_RequestHandler)
    httpd.socket.settimeout(1)
    httpd.handle_request()
    SendMSG('IOTcontroller API running on 18101')

    # ------------------------------------------------------------------------------
    #   Start WebSocket for event actions of sensors
    # ------------------------------------------------------------------------------
    #websocket.enableTrace(True)
    SendMSG('ZigBee Socket on Port '+str(ZBconfig["websocketport"]))
    SendMSG('--------------------------------------------------------------------')

    WBzbIP="ws://"+cntlINI["ZIGBEE"]["ip"]+":"+str(ZBconfig["websocketport"])
    WBws = websocket.WebSocketApp(WBzbIP,
                              on_message = WBws_message,
                              on_error = WBws_error,
                              on_close = WBws_close)
    WBws_onopen = WBws_open
    WBws.run_forever()

if __name__=="__main__":
    main()

