
IOT Controller 
Polls the sensors and sets the relays depending on the settings.   This code if fairly easy 
to follow and you can put what ever you need in this section depending upon your needs

This one is set to control 2 extract fans ,  one in the bedroom and one in the bathroom 
if the humditiy or temperture gets to high..



Setup

sudo apt install python3-gpiozero
pip3 install pynetgear


sudo nano /lib/systemd/system/IOTcontrol.service

 [Unit]
 Description=IOT Control Service
 After=multi-user.target

 [Service]
 Type=idle
 User=pi
 WorkingDirectory=/home/pi/IOT/IOTcontroller/
 ExecStart=/usr/bin/python3 /home/pi/IOT/IOTcontroller/IOTcontroller.py > /home/pi/IOT/logs/IOTcontroller$
 Restart=always

 [Install]
 WantedBy=multi-user.target



sudo chmod 644 /lib/systemd/system/IOTcontrol.service

sudo systemctl daemon-reload
sudo systemctl enable IOTcontrol.service
sudo systemctl start IOTcontrol.service
sudo systemctl status IOTcontrol.service

