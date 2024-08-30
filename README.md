IOT collection
==================================

IOTpoll
RPI GPIO on W1 poll along with zigbee sensor polling ,  packages the values into a prothemus client to allow prothemus to poll the IOTpoll module ( which i server up to grafana) 

IOTengry is an api poller (in this case an wattage reading on my main fuse box) ,  it polls APIs and creates promthemus client objects (was going to merge this and poll together at some point)

IOTcontroller ,  using zigbee and W1 sensor data,  switch relays on and off.   This is still work in progress 

IOTcontroller i use to switch on extractor fans, lights and a few other on/off things,   IOTpoll reads the relays and returns it back the grafana


