'''
Created on 22 Jan 2016
@author: lee_000
'''
import socket,urllib
import smtplib,time
 

def IPalert(IPaddr):
    to = 'lee@ssshhhh.com'
    gmail_user = 'leerobo92@gmail.com'
    gmail_pwd = 'Terry1970'
    smtpserver = smtplib.SMTP("smtp.gmail.com",587)
    smtpserver.ehlo()
    smtpserver.starttls()
    smtpserver.ehlo
    smtpserver.login(gmail_user, gmail_pwd)
    header = 'To:' + to + '\n' + 'From: ' + gmail_user + '\n' + 'Subject:testing \n'
    msg = header + '\n RPI001 IP change ' + IPaddr + '\n\n'
    smtpserver.sendmail(gmail_user, to, msg)
    print ('Email Sent '  )
    smtpserver.close
def IPpublic( ):
    import urllib.request
    f = urllib.request.urlopen('http://whatismyip.org') 
    flg=0
    for row in f:
        rs=row.decode()
        if flg==1:
            sstr=rs.find(">")+1
            estr=rs.find("<",sstr)
            IPpub=rs[sstr:estr]
            flg=0
        if rs.find('Your IP Address') >= 1: 
            flg=1
    return IPpub
def IPlocal( ):
        addr = socket.gethostbyname(socket.gethostname())
        return addr

if __name__=="__main__":
  #  print ("Checking IP "+IPpublic() )
  #  time.sleep(5)
  #  print ("Local "+IPlocal() )
   # time.sleep(5)
   # print ("Public "+IPpublic() )
   # time.sleep(5)
  #  IPalert(IPpublic() )
  
    import os, sys
    fpid = os.fork()
    if fpid!=0:
        sys.exit(0)
  
    counter = 1
    currIPpublic=IPpublic()
    IPalert(currIPpublic)
    while 1:
      counter += 1  
      time.sleep(600)
      print(currIPpublic)
      if currIPpublic!=IPpublic():
        currIPpublic=IPpublic()
        IPalert(currIPpublic)
      
    