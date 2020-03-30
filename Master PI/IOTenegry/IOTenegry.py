#!/usr/bin python3

from prometheus_client import start_http_server, Gauge
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
from systemd import journal

Ddir='/sys/bus/w1/devices/'
RelayPINS = [1,1,1,1,1,1,1,1]
config = configparser.ConfigParser()
PINS = configparser.ConfigParser()
KillSwitch = False
POLLgap={"DEF":15}
POLLlst={"DEF":0}
GaugeARR={"DEF":50}
MID=''

# Return Pin ON/OFF status
def ScrapeAPI(url,path):
    global KillSwitch
    headers = {"Content-type":  "text/plain","version":"0.0.4"}
    try:
        h4 = http.client.HTTPConnection(url.strip(),80,timeout=5)
        h4.request("POST",path.strip(),'',headers)
        rsp=h4.getresponse()
        content = rsp.read().decode('utf-8')
        return content   
    except:
        journal.send('API error '+url+' : '+sys.exc_info()[0] )
        return None;    
            
# ---------------------------------------------------------------------------

# main function
# Arg1 = R1(relays) or W1(Wire-1) 
# Arg2 = Get/Put
# Arg3 = Relay number 0-7 or SID or nothing
def main():
    global KillSwitch
    Gname=''
    rid=0
    config.read('PollAPI.ini')
    print('>>> API Scrapers')

    if "WEATHER" in config :
        print(config["WEATHER"])
        print("  Path:",config["WEATHER"]["path"])
        print("  City:",config["WEATHER"]["city"])
        print("  Cnty:",config["WEATHER"]["country"])
        print("  Path:",config["WEATHER"]["token"])
        print("  Time:",config["WEATHER"]["Time"])
        apiWEATHER=config['WEATHER']["path"]+'?city='+config["WEATHER"]["city"]+'&country='+config["WEATHER"]["country"]+'&token='+config["WEATHER"]["token"]
        print("  URL:",apiWEATHER)
        Wkey='WEATHER_'+config['WEATHER']["city"]+'_'
        GaugeARR[Wkey+'HUM']=Gauge(Wkey+'HUM','WEATHER Humidity '+config['WEATHER']["city"])
        GaugeARR[Wkey+'TEMP']=Gauge(Wkey+'TEMP','WEATHER Temp '+config['WEATHER']["city"])
        GaugeARR[Wkey+'WSPEED']=Gauge(Wkey+'WSPEED','WEATHER WindSpeed '+config['WEATHER']["city"])
        GaugeARR[Wkey+'WDIR']=Gauge(Wkey+'WDIR','WEATHER WindDir '+config['WEATHER']["city"])
       
    if "ENEGRY" in config :
        print(config["ENEGRY"])
        print("  Path:",config["ENEGRY"]["path"])
        print("  URL:",config["ENEGRY"]["url"])
        print("  Token:",config["ENEGRY"]["token"])
        print("  House:",config["ENEGRY"]["house"])
        print("  Timer:",config["ENEGRY"]["Time"])
        apiENEGRY=config['ENEGRY']["path"]+'?token='+config['ENEGRY']["token"]  
        print("  URL:",apiENEGRY)
        Ekey='ENEGRY_'+config["ENEGRY"]["house"]
        GaugeARR[Ekey]=Gauge(Ekey,'ENEGRY '+config["ENEGRY"]["house"])
        
    if "port" in config["POLL"]: 
        start_http_server(int(config['POLL']['port']))
        print('Meterics Port ',config['POLL']['port'])
        journal.send('IOTenegry Port '+config['POLL']['port'])

    else:
        start_http_server(8010)
        print('Meterics Port 8011 (Default)')

    if "Time" in config: 
        print('Poll Intervals : ',config['Time'],' Seconds')

    else:
        print('Poll Intervals : 30 Seconds')



    Egap=990
    Wgap=990
    while True:    
        Egap+=1
        if "ENEGRY" in config and Egap > int(config['ENEGRY']["Time"]):
            apiURL=config['ENEGRY']["path"]+'?token='+config['ENEGRY']["token"]      
            Rst1=json.loads(ScrapeAPI( config['ENEGRY']["url"], apiURL ))
            if Rst1 != None:
                GaugeARR[Ekey].set(Rst1['reading'])
            #print('Watts:',Rst1['reading'])
            #print('When:',Rst1['age'])
            Egap=0


        Wgap+=1
        if "WEATHER" in config and Wgap > int(config['WEATHER']["Time"]):
            apiURL=config['WEATHER']["path"]+'?city='+config["WEATHER"]["city"]+'&country='+config["WEATHER"]["country"]+'&token='+config["WEATHER"]["token"]
            Rst=json.loads(ScrapeAPI(config['WEATHER']["url"], apiURL)) 
            Wgap=0 
            if Rst != None:
                for kk in Rst:
                    kkk='WEATHER_'+config["WEATHER"]["city"]+'_'+kk
                    if kkk not in GaugeARR:
                        GaugeARR[kkk]=Gauge(kkk,'ENEGRY '+config["ENEGRY"]["house"]+' '+kk)
                        try:
                            val=int(Rst[kk])
                            GaugeARR[kkk].set(val)
                        except:
                            GaugeARR[kkk].set(0)
                            print(kk,'  No')
            else:
                GaugeARR[kkk].set(0)                
                
                #GaugeARR[kkk].set(int([kk]))
                #if isinstance(Rst[kk], float):
                #    GaugeARR[kkk].set(Rst[kk])
                #    print(kkk,Rst[kk],'  is Set float')
                #if isinstance(Rst[kk], int):  
                #    GaugeARR[kkk].set(Rst[kk])  
                #    print(kkk,Rst[kk],'  is Set Int')

            #print('Weather Humidity',str(Rst['humidity']))
            #print('Weather Pressure',str(Rst['pressure']))
            #print('Weather WindSpeed',str(Rst['windspeedKmph']))
            #print('Weather WindDir',str(Rst['winddirDegree']))
            #GaugeARR[wkey+'HUM'].set(Rst['humidity'])

            
            #{'observation_time': '07:52 PM', 'localObsDateTime': '2019-07-03 09:52 PM', 
            #'temp_C': '15', 'temp_F': '60', 'weatherCode': '116', 
            #'weatherDesc': [{'value': 'Partly cloudy'}], 
            #'windspeedMiles': '6', 'windspeedKmph': '10', 
            #'winddirDegree': '303', 'winddir16Point': 'WNW', 
            #'precipMM': '0.0', 'humidity': '38', 
            #'visibility': '10', 'pressure': '1009', 
            #'cloudcover': '38', 'FeelsLikeC': '15', 
            #'FeelsLikeF': '59', 'uvIndex': 5, 
            #'location': 'Bollnas, Sweden', 'longitude': 51.5184488, 'latitude': -0.13896069999998}


        time.sleep(1)

    sys.stdout.flush()  

if __name__=="__main__":
    main()
