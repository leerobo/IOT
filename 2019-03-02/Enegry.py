#!/usr/bin python3

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

config = configparser.ConfigParser()
KillSwitch = False

# Send Metrics  id#value
def PushGateway(idType,id):
    global KillSwitch
    ids=id.split("#")

    headers = {"Content-type":  "text/plain","version":"0.0.4"}
    url="/metrics/RPI/"+idType
    JSx=[{"MID":config["RPI"]["name"],"LID":config["RPI"]["location"],"SID":ids[0],"Value":ids[1]}]
    
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

def ProcessREPLY(RSPspt):
    if len(RSPspt) == 1:
        return
    print("Key:",RSPspt[1])

def ScrapeAPI(TKN):
    global KillSwitch
    #print(config[TKN]["url"], config[TKN]["path"], '?token='+config[TKN]["token"])
    headers = {"Content-type":  "text/plain","version":"0.0.4"}
    #try:
    h4 = http.client.HTTPConnection(config[TKN]["url"],80,timeout=5)
    if 'metric' in config[TKN]:
        ePath=config[TKN]["path"]+'?'+config[TKN]["metric"]+'&token='+config[TKN]["token"]
    else:
        ePath=config[TKN]["path"]+'?token='+config[TKN]["token"]
    #print('Path',ePath)
    h4.request("POST",ePath,'',headers)
    rsp=h4.getresponse()
    #print('{} {} - '.format(rsp.status, rsp.reason))
    content = rsp.read().decode('utf-8')
    #print( content[:200] )
    jsc=json.loads(content)
    
    if 'reading' in jsc:
        PushGateway('ENEGRY','ENEGRY#'+str(jsc['reading']))
    else:
        PushGateway('ENEGRY','HUMIDITY#'+str(jsc['humidity']))
        PushGateway('ENEGRY','PRESSURE#'+str(jsc['pressure']))
        PushGateway('ENEGRY','WINDSPEED#'+str(jsc['windspeedKmph']))
        # PushGateway('ENEGRY','WINDDIR#'+str(jsc['winddir16Point']),"STR")

        #if content[:lenx] != config["POLL"]["secret"]:
        #    print("Server Reply Invalid : Shutdown  ",content[:lenx])
            #KillSwitch=True
        #else:
        #    ProcessREPLY(content.split(" "))
        #print(content[:100], '...')
    return 0        
    #except:
    #    print("Could Not Connect : " , eURL)    
    #    return 1

# main function
# Arg1 = R1(relays) or W1(Wire-1) 
# Arg2 = Get/Put
# Arg3 = Relay number 0-7 or SID or nothing
def main():
    global KillSwitch
    config.read('Pnode.ini')
    if not config["POLL"]["Time"]:
        config["POLL"]["Time"] = 15

    print("Polling Set : ",config["POLL"]["Time"]," Seconds")
    print("Location    : ",config["RPI"]["location"])
    print("Name        : ",config["ENEGRY"]["token"])

    print('<<< Polling Enegry')
    while KillSwitch==False:
        if "ENEGRY" in config:
            ScrapeAPI( "ENEGRY" )
        if "WEATHER" in config:
            ScrapeAPI( "WEATHER" )
        else:
            KillSwitch=True
        time.sleep(int(config["POLL"]["Time"]))
    sys.stdout.flush()  

if __name__=="__main__":
    main()
