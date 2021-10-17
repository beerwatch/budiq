#!/usr/bin/env python

import gi, os
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib


class Player(object):
  def __init__(self):
    self.isPlaying=False
    self.player = Gst.ElementFactory.make("playbin","player")
    fakesink = Gst.ElementFactory.make("fakesink","fakesink")
    self.player.set_property("video-sink",fakesink)
    bus = self.player.get_bus()
    bus.add_signal_watch()
#    bus.create_watch()
    bus.connect("message",self.on_message)

  def play(self,fp):
    self.filepath=os.path.realpath(fp)
#    if self.player.get_state(1000) == Gst.State.PLAYING:
    self.player.set_state(Gst.State.NULL)
    if os.path.isfile(fp):
      self.player.set_property("uri","file://"+self.filepath)
      self.player.set_state(Gst.State.PLAYING)
      self.isPlaying=True

  def stop(self):
    self.player.set_state(Gst.State.NULL)
    self.isPlaying=False

  def on_message(self, bus, message):
    t=message.type
#    c="-"
#    print("message %d" %t , t)
    if t == Gst.MessageType.EOS:
      self.player.set_state(Gst.State.NULL)
#      self.isPlaying=False
#      self.player.set_property("uri","file://"+self.filepath)
      self.player.set_state(Gst.State.PLAYING)
#      print("EOS, restart")
    elif t == Gst.MessageType.ERROR:
      self.player.set_state(Gst.State.NULL)
      err, debug = message.parse_error()
      print("Error: %s %s", err, debug)
      self.isPlaying=False

class Player_tester(object):
  def handle_TERM(self , signal, frame):
    print('Exiting on signal')
    loop.quit()

  def __init__(self):
    import signal
    signal.signal(signal.SIGINT, self.handle_TERM)
    signal.signal(signal.SIGTERM, self.handle_TERM)

    self.player=Player()
    GLib.timeout_add_seconds(3,self._test,0)

  def _test(self, phase):
    if phase==0:
      self.player.play("mp3/Sumo.mp3")
      GLib.timeout_add_seconds(60,self._test,phase+1)
    else:
      self.player.stop()
      loop.quit()
    return False


if __name__=="__main__":

  Gst.init(None)

  print("start")

  test=Player_tester()

  loop = GLib.MainLoop()
  loop.run()

  print("exit")
