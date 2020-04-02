IOT Prometheus Client for gauges
==================================

Reads Wire-1, Pins and DHT22 and exposes the values inside the prometheus client 
add IP details to the promutheus.yml config parm on the server 

Module : IOTpoll.py

Parms : IOTpins.ini - BCM pin number allocation
        IOTpoll.ini - Promethues exposed names of the sensors


sudo nano /lib/systemd/system/IOTpoll.service

 [Unit]
 Description=IOT Control Service
 After=multi-user.target

 [Service]
 Type=idle
 User=pi
 WorkingDirectory=/home/pi/IOT/IOTpolller/
 ExecStart=/usr/bin/python3 /home/pi/IOT/IOTpolller/IOTpolller.py > /home/pi/IOT/logs/IOTpolller$
 Restart=always

 [Install]
 WantedBy=multi-user.target

 sudo chmod 644 /lib/systemd/system/IOTpoll.service

sudo systemctl daemon-reload
sudo systemctl enable IOTpoll.service
sudo systemctl start IOTpoll.service
sudo systemctl status IOTpoll.service


