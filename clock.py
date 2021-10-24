#!/usr/bin/env -S python3

BQ_PUSH1=4

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.events.readonly"]
TOKENFILE="creds/client_token.json"
CREDSFILE="creds/<your-client_secret-file>.apps.googleusercontent.com.json"
CALENDAR="<your-calendar-id-different-from-main-preferably>@group.calendar.google.com"
ALMSFETCH=6

ALMPLAYFILE='mp3/Sumo.mp3'
PREALMTIME=600
POSTALMTIME=1800

DAYSWITCH={'05:45':'dusk','07:45':'day','20:30':'dawn','21:30':'night'}
BRIGHT={'prealarm':128,'alarm':223,'night':1,'day':64,'dusk':1,'dawn':16}


import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib

import os
import signal
import time
from dateutil import parser, tz
from datetime import datetime,timedelta
import threading

from player import Player
from display import Disp
from button import Button
from caldapi import CaldAPI

TZ=tz.gettz()


class Budiq(object):
  def handle_TERM(self , signal, frame):
    print('Exiting on signal')
    loop.quit()

  def __init__(self):
    signal.signal(signal.SIGINT, self.handle_TERM)
    signal.signal(signal.SIGTERM, self.handle_TERM)
    time.tzset()

    self.isDateDesired=False
    self.isPush=False
    self.showMode='auto'	# day,night,prealarm,alarm,suppress
    self.almMode="on"		# off,on,suppress
    self.almLoad="none"		# none,loading,error
    self.alarms=[]
    self.nextAlmLoad=None
    self.almExpiryTime=None

    self.disp = Disp()
    self.disp.setShow(["----"," ---","  --","   -","  --"," ---","----","--- ","--  ","-   ","--  ","--- "],125)
    self.showTmr=GLib.timeout_add_seconds(5,self.startShow)
    self.player=Player()

    self.bt1Timer=None
    self.button1=Button(BQ_PUSH1, self.bt1handler)
    self.caldapi=CaldAPI(SCOPES,TOKENFILE,CREDSFILE,CALENDAR)

  def startShow(self):
    self.showMode='auto'
    self._updateShow()
    return False

  def stopShow(self):
    if self.showTmr!=None:
      GLib.source_remove(self.showTmr)
      self.showTmr=None

  def _updateShow(self, isSyncTimed=False):
    print('_updateShow',isSyncTimed)
    if not isSyncTimed:
      self.stopShow()
    now = datetime.now(tz=TZ)
    self.setShow(now)

# decide control mode and display brightness effects
    showMode=self.showMode
    if showMode!="alarm":
      showMode=self.whatLight(DAYSWITCH,now.strftime("%H:%M"))
      if not showMode in list(BRIGHT):
        showMode='day'

    prealm=now + timedelta(seconds=PREALMTIME)
    for alm in self.alarms:
      if prealm >= alm['tm']:
        if now >= alm['tm']:
          self.alarms.remove(alm)
#          self.nextAlmLoad=None
          self.nextAlmLoad=now+timedelta(minutes=61)
          if self.almMode=='on':
            showMode='alarm'
          if self.almMode!='off':
            self.almMode='on'
            self.almExpiryTime=now + timedelta(seconds=POSTALMTIME)
          break
        if self.almMode=='on':
          showMode='prealarm'
        break
#    print(showMode)

# stop player on expiration time if nobody seems to care
    if self.almExpiryTime and now>=self.almExpiryTime:
      self.player.stop()
      self.almExpiryTime=None

# update and execute mode change
    if showMode!=self.showMode:
      self.showMode=showMode
      self.setShow(now)
      if showMode=='alarm':
        self.disp.setBright(toBright=BRIGHT[showMode],transTime=1000, repeat=True)
        self.player.play(ALMPLAYFILE)
      else:
        self.disp.setBright(toBright=BRIGHT[showMode],transTime=1000, repeat=False)

    print('updated',now,vars(self))

# načíst alarmy, pokud jsme zasynchronizovaní a nadešel čas
    if isSyncTimed:
      self.fetchAlarms()
      return True

# a pokud nejsme v minutovém taktu, zasynchronizovat
    diff=60-now.time().second
    if diff < 1:
      diff=60
    self.showTmr=GLib.timeout_add_seconds(diff,self._updateShowSynced if diff==60 else self._updateShowUnsync)
    return False

  def _updateShowUnsync(self):
#    print('_updateShowUnsync')
    return self._updateShow(False)

  def _updateShowSynced(self):
#    print('_updateShowSynced')
    return self._updateShow(True)


  def setShow(self,now,frozen=False):
    print('set   ',now,vars(self),'frozen=',frozen)
    dot=0
    if self.almMode=='on' and len(self.alarms) > 0:
      dot|=1
    if self.isPush:
      dot|=8

    strs='    '
    if self.showMode!='night':
      if now!=None:
        strs=now.strftime("%H%M")
      if self.almLoad=="loading":
        doss=[self.dots(strs,dot & 254),self.dots(strs,dot | 1),self.dots(strs,(dot | 6) & 254),self.dots(strs,dot | 7)]
        dost=[doss[0],doss[1],doss[0],doss[1],doss[2],doss[3],doss[2],doss[3]]
        self.disp.setShow( dost ,125)
      else:
        dost=[self.dots(strs,dot),self.dots(strs,dot | 6 | (1 if self.almMode=='on' else 0) )]
        self.disp.setShow(dost,500)
    else:
      if self.almMode=='on':
        if self.almLoad=="loading":
          self.disp.setShow([self.dots(strs,1),self.dots(strs,2),self.dots(strs,1),self.dots(strs,4)],125)
        elif len(self.alarms) > 0:
          self.disp.setShow([self.dots(strs,1),self.dots(strs,1),self.dots(strs,1),self.dots(strs,2)],250)
        else:
          self.disp.setShow([self.dots(strs,2),self.dots(strs,2),self.dots(strs,2),self.dots(strs,1)],250)
      else:
        self.disp.setShow([self.dots(strs,2),self.dots(strs,4)],1000)


  def dots(self,strs,dots):
    r=""
    for i in strs:
      if dots & 1 != 0: r += "."
      dots >>= 1
      r += i
    return r


  def whatLight(self,d,e):
    p=None
    for k,v in sorted(d.items()):
      if k <= e:
        p=v
    return p if p != None else v


  def bt1handler(self,channel,val):
#    print( "hbutton: ",val)
    self.isPush=val
    if val==Button.IsDOWN:
      self.stopShow()
      if self.showMode=='prealarm':
        self.almMode='suppress'
      elif self.showMode=='alarm':
        self.player.stop()
        self.almExpiryTime=None
      elif self.showMode=='night':
        self.showMode='day'
        self.setShow(datetime.now(tz=TZ))
        self.bt1Timer=GLib.timeout_add(3000,self.bt1hShowAlm)
        return
      else:
        self.bt1hShowAlm()
        return
    else:
      if self.bt1Timer:
        GLib.source_remove(self.bt1Timer)
        self.bt1Timer=None
    self.startShow()

  def bt1hShowAlm(self):
    self.setShow(None if len(self.alarms) <1 else self.alarms[0]['tm'],frozen=True)
    self.bt1Timer=GLib.timeout_add(3000,self.bt1hToggleAlm)
    return False

  def bt1hToggleAlm(self):
    if self.almMode!='on':
      self.almMode='on'
    else:
      self.almMode='off'
    self.setShow(None if len(self.alarms) <1 else self.alarms[0]['tm'],frozen=True)
    self.nextAlmLoad=datetime.now(tz=TZ)
    self.bt1Timer=None
    return False


  def fetchAlarms(self):
    now = datetime.now(tz=TZ)
    if self.nextAlmLoad==None or self.nextAlmLoad<=now:
      background = AlmLoader(self)
      background.start()

class AlmLoader(threading.Thread):
  def __init__(self, budiq):
    threading.Thread.__init__(self)
    self.budiq = budiq

  def run(self):
    self.budiq.stopShow()
    now=datetime.now(tz=TZ)
    self.budiq.nextAlmLoad=now+timedelta(hours=7)
    self.budiq.almLoad="loading"
    self.budiq.setShow(now)
    events=self.budiq.caldapi.fetch(ALMSFETCH)
    if not events:
      self.budiq.nextAlmLoad=now+timedelta(hours=5)
      events=[]
    alarms=[]
    for event in events:
      start = event['start'].get('dateTime', event['start'].get('date'))
      tmStart=parser.parse(start)
      alarms.append( {'tm':tmStart,'summary':event['summary'] if 'summary' in dir(event) else 'unnamed' } )
    print(alarms)
    self.budiq.alarms=alarms
    self.budiq.almLoad="none"
    self.budiq.startShow()


if __name__=="__main__":

#def nope():
  Gst.init(None)

  print("start")
  budiq=Budiq()
#  for i in ['02:12','05:29','05:30','05:31','12:12','16:30','21:29','21:30','21:31','23:33']:
#    print('isDay("',i,'")',budiq.whatLight(DAYSWITCH,i))


  loop = GLib.MainLoop()
  loop.run()

  print("exit")
