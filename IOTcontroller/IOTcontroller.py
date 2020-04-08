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
#    V 0.2.1 -          - Remove REST api and tidy up code 
#  
# ----------------------------------------------------------------------------

import sys
sys.path.append('../Common')

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
from ZigBee import ZBsensors

import datetime
import configparser 

import http.client
import json


import os
import time
import glob
import socket
from array import array
#from systemd import journal
import logging
import Adafruit_DHT
import logging
import socketserver

cntlINI = configparser.ConfigParser()
cntlGPIO = configparser.ConfigParser()

Router = False
PollGAP = 10   # Poll Gap between checking sensors
LockSys = 0 

Vers='0.2.1'

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
                SendMSG('pin '+str(pin)+' set to relay')

    def ON(self, id):
        for pin in self.pins:
            if self.pins[pin]['id']==id.lower():
                SendMSG("Relay "+str(pin)+' On' )
                LED(pin).on()

    def OFF(self, id):
        for pin in self.pins:
            if self.pins[pin]['id']==id.lower():
                SendMSG("Relay "+str(pin)+' OFF' )
                LED(pin).off()

    def TOGGLEbyID(self, id):
        for pin in self.pins:
            if self.pins[pin]['id']==id.lower():
                return self.TOGGLEbyPIN(pin)

    def TOGGLEbyPIN(self,pin):
        if self.pins[pin]['type'] == 'relay':
            LED(pin).toggle()
            SendMSG('Pin '+str(pin)+' Toggled  ('+str(LED(pin).value)+')')
            return LED(pin).value
        SendMSG('Not supported yet - '+self.pins[pin]['type'] )
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

# ----------------------------------------------------------------------
#  ZigBee CALLS
# ----------------------------------------------------------------------

def ZBsetup():
    global ZBconfig, ZBsensors, ZBsensorC, LockSys
    LockSys = datetime.datetime.today()
    ZBsensorC = ZBsensors(cntlINI["ZIGBEE"]["ip"],cntlINI["ZIGBEE"]["key"])

    # params = {"words": 10, "paragraphs": 1, "format": "json"}
    # response = requests.get(f"http://"+cntlINI["ZIGBEE"]["ip"]+"/api/"+cntlINI["ZIGBEE"]["key"]+"/config")
    # if response.status_code != 200:
    #     SendMSG("ZigBee Return Error : "+str(response.status_code))
    #     return True
    # ZBconfig=response.json()
    # SendMSG("ZigBee Config Set")

def ZBchange(msg):
    jmsg=json.loads(msg)
    if 'id' not in jmsg:
        SendMSG('----Unknown Sensor Change Ignored------')
        SendMSG(msg)
        return
    IOTcntl(jmsg)  #  Core Processing 

# ----------------------------------------------------------------------
#   ZigBee DeCONz WebSocket Setup
# ----------------------------------------------------------------------

def WBws_message(ws, message):
    ZBchange(message)

def WBws_error(ws, error):
    SendMSG(error)

def WBws_close(ws):
    SendMSG("### closed ###")

def WBws_open(ws):
    def run(*args):
        for i in range(3):
            time.sleep(1)
            ws.send("Hello %d" % i)
        time.sleep(1)
        ws.close()
        SendMSG("thread terminating...")
    thread.start_new_thread(run, ())

# ----------------------------------------------------------------------
#   Decode the URL into simple Array and Dict of parms
# ----------------------------------------------------------------------

def DecodeURL(URLtxt):
    Ux= URLtxt.split('?')
    UParms = {}
    Uarr=()
    if Ux[0] == '/':  #No Url no Parms (Index)
        return Uarr,UParms

    if len(Ux) > 0:
        if Ux[0][0:1] == '/':
            Uarr=Ux[0].split('/')
    if len(Ux) == 2 or len(Ux) == 1 and Ux[0][0:1] != '/':
        if len(Ux) == 2 :
            Uprm=Ux[1].split('&')
        else:
            Uprm=Ux[0].split('&')
        for Uprms in Uprm:
            Upp=Uprms.split('=')
            UParms[Upp[0]]=Upp[1]
        
    return Uarr,UParms

# ----------------------------------------------------------------
#  Netgear API
# ----------------------------------------------------------------

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

# ------------------------------------------------------------------------
#   Log and Notifitication APIs and I/Os
# ------------------------------------------------------------------------


def WirePush(Msg,Typ):   # WirePush notifications
    r = requests.get('https://wirepusher.com/send?id=dzk6mpnEN&title=Home&message='+Msg+'&type='+Typ+'&message_id=1')
    r.status_code
def ClearMSG():
    r = requests.get('https://wirepusher.com/send?id=dzk6mpnEn&type=wirepusher_clear_notification&message_id=1')
    r.status_code
    print(r.status_code)

def SendMSG(msg):
    print(msg)
    logging.info(msg)
    #journal.send(msg)

def Alert(lvl,MsgId,msg):
    SendMSG('Alert : ('+lvl+'/'+str(MsgId)+') '+msg)

    if 'WIREPUSHER' in cntlINI:
        for WPid in cntlINI['WIREPUSHER']:
            APImsg='https://wirepusher.com/send?id='+cntlINI['WIREPUSHER'][WPid]+'&title=Home&message='+msg+'&type='+lvl+'&message_id='+str(MsgId)
            r = requests.get(APImsg)
            r.status_code

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
    global LockSys
    # print('----Event--------------------------------------------------------')
    # print(Sid)
    # print(IOTprintMSG(Sid))
    # SidID=Sid['id']
    # if 'state' in Sid :
    #     ZBsensorC.UpdSENSOR(Sid)
    # print('-----------------------------------------------------------------')

    if not ZBsensorC.Validate(SidID):
        ZBsendsorC.RefreshCONFIG()
        if not ZBsensorC.Validate(SidID):
            SendMSG('Unknown Sensor Found')
        else:
            SendMSG('New Sensor Found')

    # ----------------------- Alerts
    if  ZBsensorC.GetTYPE(SidID)=='MagSwitch':     # Doors
        if 'state' in Sid:
            if 'open' in Sid['state']:
                if Sid['state']['open']==True:
                    Alert("Door",5,ZBsensorC.GetNAME(SidID)+' Open')

    if 'config' in Sid:                            # Battery Check
        if 'battery' in Sid['config']:
            if Sid['config']['battery'] < 10:
                Alert("Battery",6,ZBsensorC.GetNAME(SidID)+' Bettery is Low')
            if Sid['config']['battery'] < 3: 
                Alert("Battery",7,ZBsensorC.GetNAME(SidID)+' Bettery is Dead')

    # ----------------------- Button Overrides
    if  ZBsensorC.GetTYPE(SidID)=='Button':
        if 'state' in Sid and 'buttoneevent' in Sid['state']:
            if Sid['state']['buttonevent'] == 1002 or Sid['state']['buttonevent'] == 1003:     # Button pressed
                GPIOpinsC.TOGGLEbyID('bedroom')
            elif Sid['state']['buttonevent']==1004:     # Button double pressed
                GPIOpinsC.TOGGLEbyID('bathroom')
            LockSys = datetime.datetime.today() + datetime.timedelta(minutes = 1)
            SendMSG(LockSys.strftime('%H:%M:%S'))

    # ----------------------- Auto Controllers
    if LockSys < datetime.datetime.today():
        if 'state' in Sid and ZBsensorC.GetNAME(SidID)=='bathroom':
            # Bathroom Controller
            if 'humidity' in Sid['state']:
                if Sid['state']['humidity'] >= 6500:
                    GPIOpinsC.ON('bathroom')
                elif Sid['state']['humidity'] <= 5500:
                    GPIOpinsC.OFF('bathroom')
            elif 'temperature' in Sid['state']:
                if Sid['state']['temperature'] >= 2600:
                    GPIOpinsC.ON('bathroom')
                elif Sid['state']['temperature'] <= 2200:
                    GPIOpinsC.OFF('bathroom')                    

        if 'state' in Sid and ZBsensorC.GetNAME(SidID)=='bedroom':
            # Bathroom Controller
            if 'humidity' in Sid['state']:
                if Sid['state']['humidity'] >= 4000:
                    GPIOpinsC.ON('bathroom')
                elif Sid['state']['humidity'] <= 3000:
                    GPIOpinsC.OFF('bathroom')
            elif 'temperature' in Sid['state']:
                if Sid['state']['temperature'] >= 2300:
                    GPIOpinsC.ON('bathroom')
                elif Sid['state']['temperature'] <= 2200:
                    GPIOpinsC.OFF('bathroom')

    LockSys = datetime.datetime.today()

   # ---------------------------------------------------------------------------

def main():
    SendMSG('Version : '+Vers)
    logging.basicConfig(filename='IOTcontroller-Events.log',format='%(levelname)s:%(message)s',level=logging.INFO)
    logging.info('Started')

    if ValidatePARMS():   #  Load in control Parms
        return
    if ZBsetup():         #  Setup deConz ZigBee
        return 

    # ------------------------------------------------------------------------------
    #   Start WebSocket for event actions of sensors
    # ------------------------------------------------------------------------------
    websocket.enableTrace(True)
    #SendMSG('ZigBee Socket on Port '+str(ZBconfig["websocketport"]))
    SendMSG('ZigBee Socket on Port '+str(ZBsensorC.configPORT()))
    SendMSG('--------------------------------------------------------------------')
    WBzbIP="ws://"+cntlINI["ZIGBEE"]["ip"]+":"+str(ZBsensorC.configPORT())
    WBws = websocket.WebSocketApp(WBzbIP,
                              on_message = WBws_message,
                              on_error = WBws_error,
                              on_close = WBws_close)
    WBws_onopen = WBws_open
    WBws.run_forever()

if __name__=="__main__":
    main()

