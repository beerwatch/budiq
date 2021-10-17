#!/usr/bin/env -S python3

BQ_PUSH1=4

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.events.readonly"]
TOKENFILE="creds/client_token.json"
CREDSFILE="creds/<your-private-api-client-secret.apps.googleusercontent.com.json"
CALENDAR="<your-dedicated-calendar-link>@group.calendar.google.com"
ALMSFETCH=6

ALMPLAYFILE='mp3/Sumo.mp3'
PREALMTIME=600
POSTALMTIME=1800

DAYSWITCH={'05:45':'dusk','07:45':'day','20:30':'dawn','21:30':'night'}
BRIGHT={'night':1,'day':64,'dusk':16,'dawn':32,'max':224}


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

    self.button1=Button(BQ_PUSH1, self.hbutton1)
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
          self.nextAlmLoad=now+timedelta(minutes=15)
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

# stop player on play expiration time if nobody seems to care
    if self.almExpiryTime and now>=self.almExpiryTime:
      self.player.stop()
      self.almExpiryTime=None

# update and execute mode change
    if showMode!=self.showMode:
      self.showMode=showMode
      self.setShow(now)
      if showMode=='alarm':
        self.disp.setBright(toBright=BRIGHT['max'],fromBright=BRIGHT[showMode],transTime=1000, repeat=True)
        self.player.play(ALMPLAYFILE)
      else:
        self.disp.setBright(toBright=BRIGHT['max' if showMode=='prealarm' else showMode],transTime=1000, repeat=False)

    print(vars(self))

# read alarms in synchronized show state when it is due to
    if isSyncTimed:
      self.fetchAlarms()
      return True

# synchronize to minute begin
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


  def hbutton1(self,channel,val):
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
        self.button1.setTimer(3000,self.bt1ShowAlm)
        return
      else:
        self.bt1ShowAlm(channel,val)
        return
    self.startShow()

  def bt1ShowAlm(self,channel,val):
    self.setShow(None if len(self.alarms) <1 else self.alarms[0]['tm'],frozen=True)
    self.button1.setTimer(3000,self.tbutton1)

  def tbutton1(self,channel,val):
    if self.almMode!='on':
      self.almMode='on'
    else:
      self.almMode='off'
    self.setShow(None if len(self.alarms) <1 else self.alarms[0]['tm'],frozen=True)
    self.nextAlmLoad=datetime.now(tz=TZ)


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
      alarms.append( {'tm':tmStart,'summary':event['summary']} )
    print(alarms)
    self.budiq.alarms=alarms
    self.budiq.almLoad="none"
    self.budiq.startShow()


if __name__=="__main__":
  Gst.init(None)

  print("start")
  budiq=Budiq()

  loop = GLib.MainLoop()
  loop.run()

  print("exit")
