class ZBsensors:
    # Store Sensors available to ZigBee and routines to extract/update info

    def __init__(self,ZBSensors):
        self.SIDX={}
        self.SID={}
        self.ZBraw={}

         # Break Sensors into a easier format to read/update
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
            
            if 'config' in ZBSensors[sid]:    
                if 'battery' in ZBSensors[sid]['config']:
                    self.ZBraw[ky+'_battery']=int(ZBSensors[sid]['config']['battery'])
                if 'temperature' in ZBSensors[sid]['config']:
                    self.ZBraw[ky+'_Temp']=float(ZBSensors[sid]['config']['temperature']/100)

            if 'state' in ZBSensors[sid]:
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

        # for sid in self.ZBraw:
        #     print(sid)
        #     print(self.ZBraw[sid])                
        # for sid in self.SID:
        #     print(self.SID[sid])

    def GetTYPE(self,ZBid):
        Etag=self.SIDX[ZBid]
        return self.SID[Etag]['type']

    def GetNAME(self,ZBid):
        Etag=self.SIDX[ZBid]
        return self.SID[Etag]['name']

    def GetSENSOR(self,ZBid):
        Etag=self.SIDX[ZBid]
        return self.SID[Etag] 

    def GetALL(self):       # Return Key,Val list
        return self.ZBraw

    def UpdSENSOR(self,Sid):
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
