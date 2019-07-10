#!/usr/bin/python

from __future__ import absolute_import, print_function, unicode_literals

from optparse import OptionParser, make_option
import os
import sys
import socket
import uuid
import dbus
import dbus.service
import dbus.mainloop.glib
#import mraa
import pyupm_th02 as th
import pyupm_guvas12d as uv
import pyupm_grove as grove
import pyupm_grovemoisture as moi
import pyupm_biss0001 as biss
import time


try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject

class Profile(dbus.service.Object):
	fd = -1

	@dbus.service.method("org.bluez.Profile1",
					in_signature="", out_signature="")
	def Release(self):
		print("Release")
		mainloop.quit()

	@dbus.service.method("org.bluez.Profile1",
					in_signature="", out_signature="")
	def Cancel(self):
		print("Cancel")

	@dbus.service.method("org.bluez.Profile1",
				in_signature="oha{sv}", out_signature="")
	def NewConnection(self, path, fd, properties):
		self.fd = fd.take()
		print("NewConnection(%s, %d)" % (path, self.fd))


		server_sock = socket.fromfd(self.fd, socket.AF_UNIX, socket.SOCK_STREAM)
		server_sock.setblocking(1)
		tem_hum= th.TH02(1,0x40)
		light = grove.GroveLight(2)
		myuv= uv.GUVAS12D(3)
		pir=biss.BISS0001(7)
		mo = moi.GroveMoisture(1)
        # mo is a boolean type which need to be transfer
		try:
			data = server_sock.recv(1024)
			print("received: %s" % data)
			while True:		
				if(data=='start'):
                    #li = light.read()
                    #ltra = uv.read()
                    #move = motion.read()
                    #mois = moist.read()
                    #server_sock.send("%s,%s,%s,%s" %(li, ltra, move, mois))				
					temp_t=str(tem_hum.getTemperature ())
					temp_humi=str(tem_hum.getHumidity ())
					temp_lit=str(light.raw_value())
					temp_u=str(myuv.value(5,1024))
					temp_m=str(mo.value())
					temp_pi=str(pir.value())
					pi="1"
					if pi=="false":
						pi="0"
					sensors=temp_t+","+temp_humi+","+temp_lit+","+temp_u+","+temp_pi+","+temp_m
					print("received: %s" % data)
					server_sock.send(sensors)
				elif(data=='stop'):
					print("stop")
					server_sock.send("stop it")
				else:
					server_sock.send("it is a wrong commond!")
		except IOError:
			pass

		server_sock.close()
		print("all done")



	@dbus.service.method("org.bluez.Profile1",
				in_signature="o", out_signature="")
	def RequestDisconnection(self, path):
		print("RequestDisconnection(%s)" % (path))

		if (self.fd > 0):
			os.close(self.fd)
			self.fd = -1

if __name__ == '__main__':
	dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

	bus = dbus.SystemBus()

	manager = dbus.Interface(bus.get_object("org.bluez",
				"/org/bluez"), "org.bluez.ProfileManager1")

	option_list = [
			make_option("-C", "--channel", action="store",
					type="int", dest="channel",
					default=None),
			]

	parser = OptionParser(option_list=option_list)

	(options, args) = parser.parse_args()

	options.uuid = "1101"
	options.psm = "3"
	options.role = "server"
	options.name = "Edison SPP Loopback"
	options.service = "spp char loopback"
	options.path = "/foo/bar/profile"
	options.auto_connect = False
	options.record = ""

	profile = Profile(bus, options.path)

	mainloop = GObject.MainLoop()

	opts = {
			"AutoConnect" :	options.auto_connect,
		}

	if (options.name):
		opts["Name"] = options.name

	if (options.role):
		opts["Role"] = options.role

	if (options.psm is not None):
		opts["PSM"] = dbus.UInt16(options.psm)

	if (options.channel is not None):
		opts["Channel"] = dbus.UInt16(options.channel)

	if (options.record):
		opts["ServiceRecord"] = options.record

	if (options.service):
		opts["Service"] = options.service

	if not options.uuid:
		options.uuid = str(uuid.uuid4())

	manager.RegisterProfile(options.path, options.uuid, opts)

	mainloop.run()

