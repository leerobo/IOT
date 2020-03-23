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
KillSwitch = False
SIDlist = {}

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
            SIDlist[SID]=0
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
    global KillSwitch
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
        content = rsp.read().decode('utf-8')
        lenx=len(config["POLL"]["secret"])
        # print(lenx,':',content[:lenx],':',config["POLL"]["secret"] )
        if content[:lenx] != config["POLL"]["secret"]:
            print("Server Reply Invalid : Shutdown  ",content[:lenx])
            #KillSwitch=True
        else:
            ProcessREPLY(content.split(" "))
        #print(content[:100], '...')
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

def ProcessREPLY(RSPspt):
    if len(RSPspt) == 1:
        return
    print("Key:",RSPspt[1])

# main function
# Arg1 = R1(relays) or W1(Wire-1) 
# Arg2 = Get/Put
# Arg3 = Relay number 0-7 or SID or nothing
def main():
    global KillSwitch
    rid=0
    config.read('Pnode.ini')
    if not config["POLL"]["Time"]:
        config["POLL"]["Time"] = 15

    print("Polling Set : ",config["POLL"]["Time"]," Seconds")
    print("Location    : ",config["RPI"]["location"])
    print("Name        : ",config["RPI"]["name"])
    
    #Initial Relays to Off 
    GPIO.setwarnings(False) 
    GPIO.setmode(GPIO.BCM)
    sidy=Wire1CNTL("GET","-1","") # Get Sensor List

    print('>>> Relays')
    for ridd in config["RID"]:
        RelaySET(ridd,"OFF")
        print("Pin ",ridd,":",config["RID"][ridd]," Off")
        Rid=PushGateway("RELAY",ridd+'#1')    # Wire1 Temp settings

    print('>>> Sensors')
    for sid in sidy.split("#"):
        if sid in config["SID"]:
            print(sid,' : ',config["SID"][sid])
        else:
            if sid !='':
                print(sid,' : ** NEW **')

    print('<<< Polling')
    while KillSwitch==False:
        # mainloop()
        sidy=Wire1CNTL("GET","-1","") # Poll Sensors
        sidv=[]                       # Hold Values
        for sid in sidy.split("#"):
            if sid != "":
                sidr=Wire1CNTL("GET",sid,"FULL")
                Rid=PushGateway("WIRE1",sidr)    # Wire1 Temp settings
        ii=0
        for ridd in config["RID"]:
            ii+=1
            if ridd != "":
                rIND=RelayGET(ridd)
                if rIND != RelayPINS[ii]:
                    RelayPINS[ii]=rIND
                    Rid=PushGateway("RELAY",ridd+'#'+str(rIND))  # Relay changed

        if "ENEGRY" in config:
            print("ENEGRY link present")

        time.sleep(int(config["POLL"]["Time"]))
    sys.stdout.flush()  

if __name__=="__main__":
    main()
