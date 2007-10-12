#!/usr/bin/env python2.5

__doc__ = """
Trap Client Demo for MeshMon
Version 0.1 - Jerry Chong <zanglang@gmail.com>
"""

import gamin
from util import MonitorThread

MONITOR_FILE = 'weathermap.conf'

class FileMonitorThread(MonitorThread):
	"""
	Monitors for changes in the filesystem
	and sends an SNMP trap
	"""
	
	def __init__(self):
		super(FileMonitorThread, self).__init__()
		self.func = self.poll_event
		self.interval = 1
		self.mon = gamin.WatchMonitor()
		#self.mon.watch_file(MONITOR_FILE, self.print_updated)
		self.mon.watch_file(MONITOR_FILE, self.notify_changed)
		
	def destroy(self):
		self.mon.stop_watch(MONITOR_FILE)
		del self.mon
		self.run_flag = 0
		
	def poll_event(self):
		if self.mon.event_pending():
			self.mon.handle_events()
	
	def print_updated(self, path, event):
		if (event is gamin.GAMChanged):
			print MONITOR_FILE, " updated! %s %s\n" % (path, event)
			
			# snmp notification
			import snmp
			from pysnmp.proto.api import v2c
			snmp.notify('localhost', (1,3,6,1,2,1,1,3,0), v2c.TimeTicks(44100))
	
	def notify_changed(self, path, event):
		if (event is gamin.GAMChanged):
			print MONITOR_FILE, " updated! %s %s\n" % (path, event)
			
			# snmp notification
			import snmp
			from pysnmp.proto.api import v2c
			snmp.notify('localhost', (1,3,6,1,2,1,1,3,0), v2c.TimeTicks(44100))
		
t = FileMonitorThread()
t.start()
while 1:
	# Wait for Ctrl-C/D
	try:
		input = raw_input()
	except (EOFError, KeyboardInterrupt):
		break;
t.destroy()