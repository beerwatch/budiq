#!/usr/bin/env python

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib

from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.virtual import sevensegment
from luma.led_matrix.device import max7219


class Disp(object):
  def __init__(self):
    self.ntick=0
    self.last=""
    self.ticker=None
    self.bright=0x70
    self.dimmer=None
    serial = spi(port=0, device=0, gpio=noop())
    device = max7219(serial) #, width=4)
    self.seg = sevensegment(device)

  def tick(self):
    if self.ntick >= len(self.texts):
      self.ntick=0
    curr=self.texts[self.ntick]
    if self.last != curr:
      self.last=curr
      self.seg.text="    "+curr[::-1]
    self.ntick+=1
    return True

  def setShow(self,texts,timeout):
    if self.ticker != None:
      GLib.source_remove(self.ticker)
      self.ticker=None
    self.ntick=0
    self.texts=texts
    self.tick()
    if timeout>0:
      self.ticker=GLib.timeout_add(timeout,self.tick)

  def setBright(self, toBright=0x70, fromBright=None, transTime=0, repeat=False):
    if self.dimmer != None:
      GLib.source_remove(self.dimmer)
    if fromBright==None:
      fromBright=self.bright
    delta=toBright-fromBright
    if delta==0:
      return

    stepTime=20
    if transTime < stepTime:
      self.bright=toBright
      self.seg.device.contrast(self.bright)
      return
    if abs(delta)*stepTime < transTime:
      stepTime=transTime//abs(delta)
    steps=transTime//stepTime
    if steps<1: steps=1
    delta=(delta+1)//steps
    if abs(delta)<1:
      delta=1 if toBright>fromBright else -1

#    self.bright=fromBright+delta//2+(1 if delta<1 else 0)
    self.bright=fromBright+delta//2
    self.seg.device.contrast(self.bright)

    self.dimmer=GLib.timeout_add(stepTime,self.dimstep, stepTime, toBright, fromBright, delta, repeat)
#    print("self.dimmer=GLib.timeout_add(",stepTime, toBright, fromBright, delta, repeat,") curr=",self.bright)

  def dimstep(self, stepTime, toBright, fromBright, delta, repeat):
#    print("dimstep(",stepTime, toBright, fromBright, delta, repeat,") curr=",self.bright)

    if abs(toBright - self.bright) > abs(delta):
      self.bright+=delta
      self.seg.device.contrast(self.bright)
      return True
    if toBright != self.bright:
      self.bright=toBright
      self.seg.device.contrast(self.bright)
      return True
    if self.dimmer != None:
      GLib.source_remove(self.dimmer)
      self.dimmer=None
    if repeat:
      self.bright=toBright-delta//2
#      if self.bright >255: self.bright=255
#      if self.bright <0:   self.bright=0
      self.seg.device.contrast(self.bright)
      self.dimmer=GLib.timeout_add(stepTime, self.dimstep, stepTime, fromBright, toBright, -delta, repeat)
#      print("  self.dimmer=GLib.timeout_add(",stepTime, fromBright, toBright, -delta, repeat,") curr=",self.bright)
    return False


class Disp_tester(object):
  def handle_TERM(self , signal, frame):
    print('Exiting on signal')
    loop.quit()

  def __init__(self):
    import signal
    signal.signal(signal.SIGINT, self.handle_TERM)
    signal.signal(signal.SIGTERM, self.handle_TERM)

    self.disp=Disp()
    self.disp.setShow(["----","---.-","--.--","-.---",".----"],250)
    GLib.timeout_add_seconds(3,self._test,0)

  def _test(self, phase):
    if phase==0:
      GLib.timeout_add_seconds(3,self._test,phase+1)
    elif phase==1:
      print("disp.setBright(toBright=255,transTime=500)")
      self.disp.setBright(toBright=255,transTime=500)
      print("-----------------------------")
      GLib.timeout_add_seconds(3,self._test,phase+1)
    elif phase==2:
      print("disp.setBright(toBright=16,transTime=1000, repeat=True)")
      self.disp.setBright(toBright=16,transTime=1000, repeat=True)
      print("-----------------------------")
      GLib.timeout_add_seconds(5,self._test,phase+1)
    elif phase==3:
      print("disp.setBright(toBright=64,transTime=100)")
      self.disp.setBright(toBright=32,transTime=100)
      print("-----------------------------")
      GLib.timeout_add_seconds(5,self._test,phase+1)
    else:
      loop.quit()

    return False


if __name__=="__main__":

  print("start")

  tester=Disp_tester()

  loop = GLib.MainLoop()
  loop.run()

  print("exit")
