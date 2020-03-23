#!/usr/bin python3

# Heat Exchanger Controller v0.0.1

from prometheus_client import start_http_server, Gauge
import Adafruit_DHT

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

Ddir='/sys/bus/w1/devices/'
RelayPINS = [1,1,1,1,1,1,1,1]
config = configparser.ConfigParser()
PINS = configparser.ConfigParser()
KillSwitch = False
POLLgap={"DEF":15}
POLLlst={"DEF":0}
GaugeARR={"DEF":50}
MID=''

def Wire1CNTL(tsk,id,fmt):
    if tsk == 'GET':
        if id == "-1":
            return GETwire1()
        else:
            DS18B20 = GETtemp(id)
            if fmt=="FULL" :
                return id+'#'+str(DS18B20)
            else:
                return DS18B20

def GETwire1():
    TotWIRE1=''
    devicelist = glob.glob(Ddir+'28*')    
    if devicelist=='':
        print('Empty')
        return TotWIRE1
    else:
        for device in devicelist:
            TT=device.split("/")
            SID = TT[len(TT)-1]
            TotWIRE1+=SID+'#'
        #   TotWIRE1.append(SID)
    return TotWIRE1

def GETtemp(SID):
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
        return "Device "+str(SID)+" Returned Read Error"

# Return Pin ON/OFF status
def RelayGET(PIN):
    GPIO.setwarnings(False) 
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(int(PIN), GPIO.OUT)
    if GPIO.input(int(PIN)):
        return 1  
    else:
        return 0   
    sys.stdout.flush()

# Toggle Pin
def RelaySET(PIN,tsk):
    GPIO.setwarnings(False) 
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(int(PIN), GPIO.OUT)
    if tsk=='ON':
       GPIO.output(int(PIN), GPIO.LOW)
       return "0"
    else:
       GPIO.output(int(PIN), GPIO.HIGH)
       return "1"        
    sys.stdout.flush()  
           
# --------------------------------------------------------------------------

# 
def main():
    global KillSwitch
    Gname=''
    rid=0
    config.read('PnodeEXCHANGE.ini')

    print("Location     : ",config["RPI"]["location"])
    print("Name         : ",config["RPI"]["name"])
    if "merticID" in config["POLL"]:
        MID=config["RPI"]["location"]+'_'+config["RPI"]["name"]+'_'
        print("Metric Prefix : ",config["POLL"]["merticID"])
    else: 
        MID=' '

    #Initial Relays to Off 
    GPIO.setwarnings(False) 
    GPIO.setmode(GPIO.BCM)

    # List Attached Sensors
    sidy=Wire1CNTL("GET","-1","")
    print('>>> Wire-1')
    for sid in sidy.split("#"):
        print
        if sid in config["SID"]:
            Gname=MID+'W1_'+config["SID"][sid]
            GaugeARR[MID+'W_S'+sid[3:]]=Gauge(Gname,'S'+sid[3:])
            print('KEY:'+Gname,' TYPE:W1   SID:',sid[3:])
        else:
            if sid !='':
                GaugeARR[MID+'W_S'+sid[3:]]=Gauge(MID+'W_S'+sid[3:],'**(undefined)**')
                print('KEY:'+MID+'W_S'+sid[4:],' TYPE:**NEW**')

    if "port" in config["POLL"]: 
        start_http_server(int(config['POLL']['port']))
        print('Meterics Port ',config['POLL']['port'])
    else:
        start_http_server(8010)
        print('Meterics Port 8010 (Default)')

    if "Time" in config: 
        print('Poll Intervals : ',config['Time'],' Seconds')
    else:
        print('Poll Intervals : 30 Seconds')

    while True:    
        sidy=Wire1CNTL("GET","-1","") # Poll Sensors
        sidv=[]                       # Hold Values
        for sid in sidy.split("#"):
            if sid != "":
                sidr=Wire1CNTL("GET",sid,"FULL")
                val=sidr.split("#")
                GaugeARR[MID+'W_S'+sid[3:]].set(val[1])

        for Pin in PINS:
            if Pin != "DEFAULT":
                if PINS[Pin]["Type"]=='AM2302' or  PINS[Pin]["Type"]=='DHT22':
                    humidity,temperature = Adafruit_DHT.read_retry(22, Pin)
                    if isinstance(temperature, float):
                        GaugeARR[MID+'PIN_'+Pin+'_TEMP'].set(temperature)
                    if isinstance(humidity, float):
                        GaugeARR[MID+'PIN_'+Pin+'_HUM'].set(humidity)
                if PINS[Pin]["Type"]=='Relay':
                    GaugeARR[MID+'RELAY_'+Pin].set(RelayGET(Pin))

        if "Time" in config: 
            time.sleep(config['Time'])
        else:
            time.sleep(30)

    sys.stdout.flush()  

if __name__=="__main__":
    main()
