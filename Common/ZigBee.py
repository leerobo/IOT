import requests

class ZBsensors:

    # Store Sensors available to ZigBee and routines to extract/update info

    def __init__(self,ZBip,ZBkey):
        self.SIDX={}
        self.SID={}
        self.ZBraw={}

        # Get Sensor list
        response = requests.get(f"http://"+ZBip+"/api/"+ZBkey+"/sensors/")
        if response.status_code != 200:
            return False
        # print("Sensors:",response.json())
        self.RequestSENSORS(response.json())

        # Get conroller settings
        response = requests.get(f"http://"+ZBip+"/api/"+ZBkey+"/config")
        if response.status_code != 200:
            return True
        # print("Controller:",response.json())
        self.RequestCONFIG(response.json())

    def RefrestSENSORS(self):
        # Connect to Zigbee controller
        response = requests.get(f"http://"+ZBip+"/api/"+ZBkey+"/sensors/")
        if response.status_code != 200:
            return False
        self.SIDX.clear()
        self.SID.clear()
        self.ZBraw.clear()
        self.RequestSENSORS(response.json())

    def RequestSENSORS(self,ZBSensors):
         # Break Sensors into a easier format to read/update
         # SIDx index is between etag (unique sensor MAC codes), and zigbee array ID (SID)
         # RAW is the original json , SID is the values of the sensors
        for sid in ZBSensors:
            self.SIDX[sid]=ZBSensors[sid]['etag']
            etag=ZBSensors[sid]['etag']
            
            if etag not in self.SID:
                self.SID[etag]={}
                self.SID[etag]['name']=ZBSensors[sid]['name']
                self.SID[etag]['modelid']=ZBSensors[sid]['modelid']
                if ZBSensors[sid]['modelid'] == 'lumi.remote.b1acn01':
                    self.SID[etag]['type']='Button'
                elif ZBSensors[sid]['modelid'] == 'lumi.weather':
                    self.SID[etag]['type']='MultiSensor'
                elif ZBSensors[sid]['modelid'] == 'lumi.sensor_magnet.aq2':
                    self.SID[etag]['type']='MagSwitch'
                elif ZBSensors[sid]['modelid'] == 'PHDL00':
                    self.SID[etag]['type']='Controller'
                else:
                    self.SID[etag]['type']='N/A'

            if 'config' in ZBSensors[sid]:    
                if 'battery' in ZBSensors[sid]['config']:
                    self.SID[etag]['battery']=ZBSensors[sid]['config']['battery']
                if 'temperature' in ZBSensors[sid]['config']:
                    self.SID[etag]['temp']=ZBSensors[sid]['config']['temperature']

            if 'state' in ZBSensors[sid]:
                if 'temperature' in ZBSensors[sid]['state']:
                    self.SID[etag]['temp']=ZBSensors[sid]['state']['temperature']                    
                if 'humidity' in ZBSensors[sid]['state']:
                    self.SID[etag]['hum']=ZBSensors[sid]['state']['humidity']                    
                if 'pressure' in ZBSensors[sid]['state']:
                    self.SID[etag]['Pres']=ZBSensors[sid]['state']['pressure']                    
                if 'open' in ZBSensors[sid]['state']:
                    self.SID[etag]['open']=ZBSensors[sid]['state']['open']
                if 'lastupdated' in ZBSensors[sid]['state']:
                    self.SID[etag]['lastupdated']=ZBSensors[sid]['state']['lastupdated']
          
        for sid in ZBSensors:
            ky='ZB_'+ZBSensors[sid]['name'].replace(' ','_')
            ky=ky+'_'+ZBSensors[sid]['modelid'].replace('.','_')

            LostSensor=False
            if 'config' in ZBSensors[sid]:  
                if 'reachable' in ZBSensors[sid]['config']:
                    if ZBSensors[sid]['config']['reachable'] == False:
                        print(ky,':Lost Sensor')
                        LostSensor=True

            if 'config' in ZBSensors[sid] and not LostSensor:  
                if 'battery' in ZBSensors[sid]['config']:
                    if ZBSensors[sid]['config']['battery'] != 'None':
                        self.ZBraw[ky+'_battery']=int(ZBSensors[sid]['config']['battery'])
                if 'temperature' in ZBSensors[sid]['config']:
                    self.ZBraw[ky+'_Temp']=float(ZBSensors[sid]['config']['temperature']/100)

            if 'state' in ZBSensors[sid] and not LostSensor:  
                if 'temperature' in ZBSensors[sid]['state']:
                    self.ZBraw[ky+'_Temp']=float(ZBSensors[sid]['state']['temperature']/100)
                if 'humidity' in ZBSensors[sid]['state']:
                    self.ZBraw[ky+'_Hum']=float(ZBSensors[sid]['state']['humidity']/100)
                if 'pressure' in ZBSensors[sid]['state']:
                    self.ZBraw[ky+'_Pressure']=int(ZBSensors[sid]['state']['pressure'])
                if 'open' in ZBSensors[sid]['state']:
                    if ZBSensors[sid]['state']['open'] == True:
                        self.ZBraw[ky+'_Open']=1
                    else:
                        self.ZBraw[ky+'_Open']=0        

    def RequestCONFIG(self,ZBconfig):
         # Break Sensors into a easier format to read/update
        self.ZBconfig = ZBconfig

    def GetTYPE(self,ZBid):
        Etag=self.SIDX[ZBid]
        return self.SID[Etag]['type']

    def GetNAME(self,ZBid):
        Etag=self.SIDX[ZBid]
        return self.SID[Etag]['name']

    def GetSENSOR(self,ZBmac):  # Return Sensor details based on MAC
        Etag=self.SIDX[ZBmac]
        return self.SID[Etag]

    def GetMAC(self,ZBmac):   # Return Sensors MAC id from SID
        print('ZB:GETMAC:',self.SIDX,':',ZBmac,':',self.SIDX[ZBmac])
        return self.SIDX[ZBmac]

    def GetALL(self):         # Return Key,Val list
        return self.ZBraw

    def Validate(self,ZBsid):  # Check if Sensor is set, based on Sensor ID in SIDx
        if ZBsid in self.SIDX:
            return True
        return False

    def UpdSENSOR(self,Sid):  # Update Sensor base on SID
        ZBid = Sid['id']
        etag=self.SIDX[ZBid]
        if 'lastupdated' in Sid['state']:
            self.SID[etag]['lastupdated']=Sid['state']['lastupdated']
        if 'humidity' in Sid['state']:
            print(str(ZBid)+' - Hum was '+str(self.SID[etag]['hum'])+' Now '+str(Sid['state']['humidity']))
            self.SID[etag]['hum']=Sid['state']['humidity']
        if 'temperature' in Sid['state']:
            print(str(ZBid)+' - Temp was '+str(self.SID[etag]['temp'])+' Now '+str(Sid['state']['temperature']))
            self.SID[etag]['temp']=Sid['state']['temperature']
        if 'pressure' in Sid:
            self.SID[etag]['pres']=Sid['state']['pressure']

    def CheckBATTERY(self):
        prvEid=' '
        for sid in self.ids:
            if 'battery' in self.ids[sid]['config'] and prvEid != self.ids[sid]['etag'] :
                if self.ids[sid]['config']['battery'] != None:
                    if int(self.ids[sid]['config']['battery']) < 40 :
                        prvEid=self.ids[sid]['etag']
                        Alert("Battery",1,self.ids[sid]['name']+' Sensor  battery @ '+str(self.ids[sid]['config']['battery'])+'%  ['+prvEid+']' )

    def configPORT(self):       # Return Socket Port number
        print(self.ZBconfig)
        if 'websocketport' in self.ZBconfig:
            return self.ZBconfig['websocketport']
        return 80
