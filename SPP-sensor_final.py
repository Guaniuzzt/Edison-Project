#!/usr/bin/python

from __future__ import absolute_import, print_function, unicode_literals

from optparse import OptionParser, make_option
import os,threading
import sys
import socket
import uuid
import dbus
import dbus.service
import dbus.mainloop.glib
import mraa
class th02:
	BUS_ID = 6
	ADDRESS = 0x40

	TH02_REG_STATUS = 0x00
	TH02_REG_DATA_H = 0x01
	TH02_REG_DATA_L = 0x02
	TH02_REG_CONFIG = 0x03
	TH02_REG_ID = 0x11

	TH02_STATUS_RDY_MASK = 0x01

	TH02_CMD_MEASURE_HUMI = 0x01
	TH02_CMD_MEASURE_TEMP = 0x11

	def __init__(self):
		self.bus = mraa.I2c(self.BUS_ID)
		self.bus.address(self.ADDRESS)
		self.bus.read(3)
	def getTemperature(self):
		self.bus.writeReg(self.TH02_REG_CONFIG,self.TH02_CMD_MEASURE_TEMP)
		while not self.getStatusSuccess(): pass
		t_raw = self.bus.read(3)
		temperature = (t_raw[1]<<8|t_raw[2])>>2
		return (temperature/32.0)-50.0
		
	def getHumidity(self):
		self.bus.writeReg(self.TH02_REG_CONFIG,self.TH02_CMD_MEASURE_HUMI)
		while not self.getStatusSuccess(): pass
		t_raw = self.bus.read(3)
		humidity = (t_raw[1]<<8|t_raw[2])>>4
		return (humidity/16.0)-24.0
		
	def getStatusSuccess(self):
		success = (self.bus.readReg(self.TH02_REG_STATUS) & self.TH02_STATUS_RDY_MASK) == 0
		return success
moist = mraa.Aio(1)
light = mraa.Aio(2)
uv = mraa.Aio(3)
motion = mraa.Gpio(7)
i2c = th02()
try:
	from gi.repository import GObject
except ImportError:
	import gobject as GObject



class Profile(dbus.service.Object):
	fd = -1
	@dbus.service.method("org.bluez.Profile1",in_signature="",out_signature="")
	def Release(self):
		print("Release")
		mainloop.quit()

	@dbus.service.method("org.bluez.Profile1",in_signature="",out_signature="")
	def Cancel(self):
		print("Cancel")

	@dbus.service.method("org.bluez.Profile1",in_signature="",out_signature="")
	def NewConnection(self, path, fd, properties):
		self.fd = fd.take()
		print("NewConnection(%s, %d)" % (path, self.fd))
		server_sock = socket.fromfd(self.fd, socket.AF_UNIX,socket.SOCK_STREAM)
		server_sock.setblocking(1)
		print("This is Edison SPP Sensor loopback service\n\
Send ,sensor, to recieve new sensor data\n\
Else all data will be loopback\n\
Please start:\n")
		try:
			while True:
				data = server_sock.recv(1024)
				print("received: %s" % data)
				while (data == 'sensor'):
					temp = i2c.getTemperature()
					humi = i2c.getHumidity()
					li = light.read()
					ltra = uv.read()
					move = motion.read()
					mois = moist.read()
				        server_sock.send("%d,%d,%d,%d,%d,%d;" %(temp,humi,li, ltra, move, mois))
				else:
					server_sock.send("looping back: %s\n" %data)
		except IOError:
			pass
		server_sock.close()
		print("all done")

	@dbus.service.method("org.bluez.Profile1",in_signature="o", out_signature="")
	def RequestDisconnection(self, path):
		print("RequestDisconnection(%s)" % (path))
		if (self.fd > 0):
			os.close(self.fd)
			self.fd = -1

if __name__ == '__main__':
	dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
	bus = dbus.SystemBus()
	manager = dbus.Interface(bus.get_object("org.bluez","/org/bluez"),"org.bluez.ProfileManager1")
	option_list = [make_option("-C", "--channel", action="store",type="int", dest="channel",default=None),]
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
	opts = {"AutoConnect" : options.auto_connect,}
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
