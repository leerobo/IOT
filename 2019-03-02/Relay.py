#!/usr/bin python3

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

# Send Metrics  id#value
def PushGateway(idType,id):
    ids=id.split("#")
    idname=ids[0]
    if idType == "WIRE1":
        if ids[0] in config["SID"]:
            idname=config["SID"][ids[0]] 
    elif idType == "RELAY":
        if ids[0] in config["RID"]:
            idname=config["RID"][ids[0]] 
    else:
        idname=ids[0]
    #print(ids[0],idname,ids[1])

    headers = {"Content-type":  "text/plain","version":"0.0.4"}
    url="/metrics/RPI/"+idType
    JSx=[{"MID":config["RPI"]["name"],"LID":config["RPI"]["location"],"SID":idname,"Value":ids[1]}]
    try:
        Body = json.dumps(JSx) 
        h4 = http.client.HTTPConnection(config["POLL"]["server"], config["POLL"]["port"],timeout=5)
        h4.request("POST", url,Body,headers)
        rsp=h4.getresponse()
        # print('{} {} - '.format(rsp.status, rsp.reason))
        # content = rsp.read().decode('utf-8')
        # print(content[:100], '...')
        return 0        
    except:
        print("Could Not Connect : " , config["POLL"]["server"])    
        return 1

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
       return 0
    else:
       GPIO.output(int(PIN), GPIO.HIGH)
       return 1        
    sys.stdout.flush()  

# main function
# Arg1 = PIN number 
def main():
    config.read('Pnode.ini')
    print('Relay:',sys.argv[1])
    if sys.argv[1] in config["RID"]:
       print('Pin  :',sys.argv[1])
       print('Desc :',config["RID"][sys.argv[1]])
       cid=RelayGET(sys.argv[1])
       if cid == 1:
           RelaySET(sys.argv[1],'ON')
           print('ON')
       else:
           RelaySET(sys.argv[1],'OFF')
           print('OFF') 
    else:
        print ('Relay PIN not defined')
        print(config["RID"])
    sys.stdout.flush()  

if __name__=="__main__":
    main()
