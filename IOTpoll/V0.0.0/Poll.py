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

import Adafruit_DHT

Ddir='/sys/bus/w1/devices/'
RelayPINS = [1,1,1,1,1,1,1,1]
config = configparser.ConfigParser()
PINS = configparser.ConfigParser()
KillSwitch = False
POLLgap={"DEF":15}
POLLlst={"DEF":0}

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
def PushGateway(idType,idName,idValue):
    global KillSwitch
    #print(idType,idName,idValue)

    headers = {"Content-type":  "text/plain","version":"0.0.4"}
    url="/metrics/RPI/"+idType
    idValueCHR=str(idValue)
    JSx=[{"MID":config["RPI"]["name"],"LID":config["RPI"]["location"],"SID":idName,"Value":idValueCHR}]
    #print(JSx)
    try:
        Body = json.dumps(JSx) 
        h4 = http.client.HTTPConnection(config["POLL"]["server"], config["POLL"]["port"],timeout=5)
        h4.request("POST", url,Body,headers)
        rsp=h4.getresponse()
        #print('{} {} - '.format(rsp.status, rsp.reason))
        content = rsp.read().decode('utf-8')
        lenx=len(config["POLL"]["secret"])
        #print(lenx,':',content[:lenx],':',config["POLL"]["secret"] )
        if content[:lenx] != config["POLL"]["secret"]:
            print("Server Reply Invalid : Shutdown  ",content[:lenx],"-",config["POLL"]["secret"])
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
       return "0"
    else:
       GPIO.output(int(PIN), GPIO.HIGH)
       return "1"        
    sys.stdout.flush()  

def ProcessREPLY(RSPspt):
    if len(RSPspt) == 1:
        return
    print("Key:",RSPspt[1])

def PINaction(Pin):
    #print(Pin)
    if PINS[Pin]["Type"]=='AM2302' or  PINS[Pin]["Type"]=='DHT22':
        humidity,temperature = Adafruit_DHT.read_retry(22, Pin)
        #print('Temp={0:0.1f}*C  Humidity={1:0.1f}%'.format(temperature, humidity))
        PushGateway("PIN",PINS[Pin]['NAME']+'_TEMP',temperature)
        PushGateway("PIN",PINS[Pin]['NAME']+'_HUM',humidity)   
        return 0
    if PINS[Pin]["Type"]=='Relay':
        PushGateway("RELAY",PINS[Pin]['NAME'],RelayGET(Pin))  # Relay changed
        return 0
    return 0

def ScrapeAPI(url,path):
    global KillSwitch
    headers = {"Content-type":  "text/plain","version":"0.0.4"}
    #try:
    h4 = http.client.HTTPConnection(url.strip(),80,timeout=5)
    h4.request("POST",path.strip(),'',headers)
    rsp=h4.getresponse()
    #print('{} {} - '.format(rsp.status, rsp.reason))
    content = rsp.read().decode('utf-8')
    #print( content[:200] )
    return content
    
    #if 'reading' in jsc:
    #    PushGateway('ENEGRY','ENEGRY#',str(jsc['reading']))
    #else:
    #    PushGateway('ENEGRY','HUMIDITY',str(jsc['humidity']))
    #    PushGateway('ENEGRY','PRESSURE',str(jsc['pressure']))
    #    PushGateway('ENEGRY','WINDSPEED',str(jsc['windspeedKmph']))
        # PushGateway('ENEGRY','WINDDIR#'+str(jsc['winddir16Point']),"STR")

        #if content[:lenx] != config["POLL"]["secret"]:
        #    print("Server Reply Invalid : Shutdown  ",content[:lenx])
            #KillSwitch=True
        #else:
        #    ProcessREPLY(content.split(" "))
        #print(content[:100], '...')
    #return 0        

def POLLnow(AREA):
    if AREA in POLLgap:
        gap=POLLgap[AREA]
    else:
        gap=POLLgap["DEF"]
    now = datetime.datetime.now()
    #print(now,gap,AREA)
    if AREA in POLLlst: 
        #print('LstTme:',POLLlst[AREA] )
        #print(POLLlst[AREA] + datetime.timedelta(0,int(gap))  )
        if now >  ( POLLlst[AREA] + datetime.timedelta(0,int(gap)) ):
            POLLlst[AREA]=now
            print(AREA," True")
            return True
        else:
            #print(AREA," False")
            return False
    else:
        POLLlst[AREA]=now
        #print(AREA," True2")
        return True
    
            
# ---------------------------------------------------------------------------



# main function
# Arg1 = R1(relays) or W1(Wire-1) 
# Arg2 = Get/Put
# Arg3 = Relay number 0-7 or SID or nothing
def main():
    global KillSwitch
    rid=0
    config.read('Pnode.ini')
    PINS.read('PnodePIN.ini')

    if config["POLL"]["Time"]:
        POLLgap["DEF"]=config["POLL"]["Time"]

    print("Default Poll : ",config["POLL"]["Time"]," Seconds")
    print("Location     : ",config["RPI"]["location"])
    print("Name         : ",config["RPI"]["name"])
    print("Master       : ",config["POLL"]["server"])

    if "ENERGY" in config:
        print("Energy       : ",config["ENERGY"]["city"],' / ',config["ENERGY"]["country"])
        if config["ENERGY"]["Time"]:
            POLLgap['ENERGY']=config["ENERGY"]["Time"]
            print("Energy Poll  : ",config["ENERGY"]["Time"])

    if "WEATHER" in config:
        print("Weather      : ",config["WEATHER"]["city"],' / ',config["WEATHER"]["country"])
        if config["WEATHER"]["Time"]:
            POLLgap['WEATHER']=config["WEATHER"]["Time"]
            print("Weather Poll : ",config["WEATHER"]["Time"])

    #Initial Relays to Off 
    GPIO.setwarnings(False) 
    GPIO.setmode(GPIO.BCM)
    sidy=Wire1CNTL("GET","-1","")

    print('>>> Pins')
    if "Time" in PINS:
        POLLgap['PINS']=config["PINS"]["Time"]
        print("Pin Poll    : ",PINseconds)
    for pin in PINS:
        if pin!="DEFAULT":
            print("Pin ",pin,":",PINS[pin]["Type"],"-",PINS[pin]["Name"])

    print('>>> Wire-1')
    for sid in sidy.split("#"):
        if sid in config["SID"]:
            print(sid,' : ',config["SID"][sid])
        else:
            if sid !='':
                print(sid,' : ** NEW **')

    print('<<< Polling')
    while KillSwitch==False:

        if "SIDS" in config and POLLnow("WIRE1"):
            sidy=Wire1CNTL("GET","-1","") # Poll Sensors
            sidv=[]                       # Hold Values
            for sid in sidy.split("#"):
                if sid != "":
                    sidr=Wire1CNTL("GET",sid,"FULL")
                    val=sidr.split("#")
                    Rid=PushGateway("WIRE1",config["SID"][sid],val[1])    # Wire1 Temp settings

        if  POLLnow("PINS"):
            for pin in PINS:
                if pin != "DEFAULT":
                    rc=PINaction(pin)      
    
        if "ENERGY" in config and POLLnow("ENERGY"):
            apiURL=config['ENERGY']["path"]+'?token='+config['ENERGY']["token"]      
            Rst1=json.loads(ScrapeAPI( config['ENERGY']["url"], apiURL ))
            for kk in Rst1[0]['data'][0]:
                PushGateway('ENERGY',config['ENERGY']["city"],str(Rst1[0]['data'][0][kk]))

        if "WEATHER" in config and POLLnow("WEATHER"):
            apiURL=config['WEATHER']["path"]+'?city='+config["WEATHER"]["city"]+'&country='+config["WEATHER"]["country"]+'&token='+config["WEATHER"]["token"]
            Rst=json.loads(ScrapeAPI(config['WEATHER']["url"], apiURL))     
            PushGateway('WEATHER','HUMIDITY',str(Rst['humidity']))
            PushGateway('WEATHER','PRESSURE',str(Rst['pressure']))
            PushGateway('WEATHER','WINDSPEED',str(Rst['windspeedKmph']))
            PushGateway('WEATHER','WINDDIR',str(Rst['winddirDegree']))

        time.sleep(1)  # Nap for a second

    sys.stdout.flush()  

if __name__=="__main__":
    main()
