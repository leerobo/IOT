import os,glob

class PinControl:
        
    def __init__(self):
        self.Wire1Dir='/sys/bus/w1/devices/'
        self.Wire1List={}

    def w1Refresh(self):
      if not os.path.exists(self.Wire1Dir):
           return {'message':'Wire-1 Not present : use rasphi-config to switch Wire 1 on on GPIO4'},400
      devicelist = glob.glob(self.Wire1Dir+'28*')    
      for device in devicelist:
          TT=device.split("/")
          SID = TT[len(TT)-1]
          w1,status=self.w1Read(TT[len(TT)-1])
          self.Wire1List['W1_S'+SID[3:]]=w1
      return {'message':str(len(self.Wire1List))+' Sensors Found'},200

    def w1Read(self,SID):
       devicefile=self.Wire1Dir+SID+'/w1_slave'
       try:
         fileobj = open(devicefile,'r')
         lines = fileobj.readlines()
         fileobj.close()
       except:
         return {'message':'Sensors Read Error','sid':SID},400

       # get the status from the end of line 1 
       status = lines[0][-4:-1]

       # is the status is ok, get the temperature from line 2
       if status=="YES":
         equals_pos = lines[1].find('t=')
         temp_string = lines[1][equals_pos+2:]
         tempvalue=float(temp_string)/1000
         return {'value':tempvalue},200
       else:
         return {'message':'Sensors Reading Error','sid':SID},400