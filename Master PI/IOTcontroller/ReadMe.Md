Setup SOP

sudo apt install python3-gpiozero
pip3 install pynetgear


sudo nano /lib/systemd/system/IOTcontrol.service

 [Unit]
 Description=IOT Poll Service
 After=multi-user.target

 [Service]
 Type=idle
 User=pi
 WorkingDirectory=/home/pi/Pnode/V1/
 ExecStart=/usr/bin/python3 /home/pi/Pnode/V1/IOTcontrol.py > /home/pi/Pnode/V1/IOT.log 2>&1
 Restart=always

 [Install]
 WantedBy=multi-user.target


sudo chmod 644 /lib/systemd/system/IOTcontrol.service

sudo systemctl daemon-reload
sudo systemctl enable IOTcontrol.service
sudo systemctl start IOTcontrol.service
sudo systemctl status IOTcontrol.service

