#!/usr/bin/env python

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib

import RPi.GPIO as GPIO

BQ_PUSH1=4


class Button(object):
  IsDOWN=1
  IsUP=0
  def __init__(self, channel=BQ_PUSH1, handler=None):
    self.channel=channel
    self.extHandler=handler
    self.keepVal=self.IsUP
    self.keepCnt=1
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(self.channel, GPIO.IN , pull_up_down=GPIO.PUD_UP )
    GPIO.add_event_detect(self.channel, GPIO.FALLING, callback=self.handleFall, bouncetime=63)

  def handleFall(self , channel):
    if self.keepVal==self.IsDOWN:
      return
    self.keepVal=self.IsDOWN
    self.keepCnt=3
    if self.extHandler!=None:
      self.extHandler(channel,self.keepVal)
    GLib.timeout_add(37,self.handleKeeper)

  def handleKeeper(self):
    val=GPIO.input(self.channel)
    if self.keepVal==self.IsDOWN:
      if val==GPIO.LOW:
        self.keepCnt=3
        return True
      self.keepCnt-=1
      if self.keepCnt>0:
        return True
      self.keepVal=self.IsUP
      if self.extHandler!=None:
        self.extHandler(self.channel,self.keepVal)
    return False


class Button_tester(object):
  def __init__(self):
    import signal
    signal.signal(signal.SIGINT, self.handle_TERM)
    signal.signal(signal.SIGTERM, self.handle_TERM)
    self.button1=Button(handler=self.hbutton1)

  def hbutton1(self,channel,val):
    print( "hbutton: ",val)
#    if val==Button.IsDOWN:
#      self.button1.setTimer(750,self.tbutton1)

  def tbutton1(self,channel,val):
    print( "tbutton: ",val)
    if val==Button.IsDOWN:
      self.button1.setTimer(2500,self.tbutton1)

  def handle_TERM(self , signal, frame):
    print('Exiting on signal')
    loop.quit()


if __name__=="__main__":
  print("button1 tester start")


  button1=Button_tester()

  loop = GLib.MainLoop()
  loop.run()

  GPIO.cleanup()
  print("exit")
