sudo pip3 install prometheus-client
sudo pip3 install Adafruit_DHT


sudo nano /lib/systemd/system/IOTpoll.service

 [Unit]
 Description=IOT Poll Service
 After=multi-user.target

 [Service]
 Type=idle
 User=pi
 WorkingDirectory=/home/pi/Pnode/
 ExecStart=/usr/bin/python3 /home/pi/Pnode/IOTpoll.py > /home/pi/Pnode/IOT.log 2>&1
 Restart=always

 [Install]
 WantedBy=multi-user.target


sudo chmod 644 /lib/systemd/system/IOTpoll.service

sudo systemctl daemon-reload
sudo systemctl enable IOTpoll.service
sudo systemctl start IOTpoll.service
sudo systemctl status IOTpoll.service



Test API GPIO on port 18100:-
http://192.168.2.19:18100/?API=7483&TYP=RLY         // Show all relays
http://192.168.2.19:18100/?API=7483&TYP=RLY&RLY=6   // toggle



Gmail code : sdfghiuytr765


IOTcontroller.py
PYNETGEAR 
pip3 install pynetgear