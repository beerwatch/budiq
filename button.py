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
    self.handler=handler
    self.timer=None
    self.timehandler=None
    self.lastval=GPIO.HIGH
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(self.channel, GPIO.IN , pull_up_down=GPIO.PUD_UP )
    GPIO.add_event_detect(self.channel, GPIO.BOTH, callback=self.handleEventUD , bouncetime=133)

  def handleEventUD(self , channel):
    val=GPIO.input(channel)
    if val==self.lastval:
      val=1-val
    self.lastval=val
    self.handleEvent(channel, self.IsDOWN if self.lastval==GPIO.LOW else self.IsUP)

  def handleEvent(self , channel, val):
    if self.timer!=None:
      GLib.source_remove(self.timer)
      self.timer=None
    if self.handler!=None:
      self.handler(channel,val)

  def setTimer(self, timeout, timeHandler):
    self.timehandler=timeHandler
    self.timer=GLib.timeout_add(timeout,self.handleTimer)

  def handleTimer(self):
    if self.timehandler!=None:
      self.timer=None
      self.timehandler(self.channel,self.IsDOWN if self.lastval==GPIO.LOW else self.IsUP)
    return False


class Button_tester(object):
  def __init__(self):
    import signal
    signal.signal(signal.SIGINT, self.handle_TERM)
    signal.signal(signal.SIGTERM, self.handle_TERM)
    self.button1=Button(handler=self.hbutton1)

  def hbutton1(self,channel,val):
    print( "hbutton: ",val)
    if val==Button.IsDOWN:
      self.button1.setTimer(750,self.tbutton1)

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
