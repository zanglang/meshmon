#!/usr/bin/env python2.5

__doc__ = """
Link Monitor for MeshMon
Version 0.1 - Jerry Chong <zanglang@gmail.com>

Based on meshmon.pl by Dirk Lessner, National ICT Australia
"""

from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.smi import builder
from threading import Thread
from trafficmon import snmp_walk, snmp_get, snmp_bulk_get, MonitorThread
import config
import logging
import os, sys

if (config.Debug):
	logging.basicConfig(level=logging.DEBUG)

# pool for monitor and graph threads
ThreadPool = []

# create MIB builder and get object definitions
ifMib = builder.MibBuilder().loadModules('SNMPv2-MIB', 'IF-MIB', 'RFC1213-MIB')

# global routing table store
Routes = {}

#------------------------------------------------------------------------------ 
class LinkMon:
	
	def __init__(self):
		print 'TrafficMon started.\n' + \
			'Press <Ctrl>-C to shut down.'
			
	def destroy(self):
		""" Cleaning up """
		
		print 'Please wait while TrafficMon shuts down...'
		# stop worker threads
		for thread in ThreadPool:
			thread.run_flag = 0
			try: thread.join()
			except: pass
		logging.shutdown()
		sys.exit()
		
	def main(self):
		""" Main procedure """
		
		# TODO: extra options for linkmon?
		self.options = {
			'dir': config.RrdPath,
			'ext': config.ImgFormat.lower(),
			'imgdir': config.ImgPath,
			'int': config.GraphInterval,
			'topologyimg': config.TopologyImg
		}
		
		global Routes
		# initialize each monitored node
		for node in config.Nodes:
			logging.debug('Initializing WLAN interfaces for ' + `node`)
			# initialize routing tables store
			Routes[node] = {}
			# initialize monitoring interfaces
			self.init_interfaces(node)
		
		# If we have worker threads running...
		if len(ThreadPool) > 0:
			print `len(ThreadPool)` + ' threads executing...'		
			while 1:
				# Wait for Ctrl-C/D
				try:
					input = raw_input()
				except (EOFError, KeyboardInterrupt):
					break;
		else:
			# no threads running at all! (possibly bad configuration)
			print 'Nothing to monitor.'
		self.destroy()
		
	def init_interfaces(self, target):
		""" Check target node interfaces """
		
		# SNMP GET
		try:
			oids = snmp_walk(target,
				ifMib.importSymbols('IF-MIB', 'ifDescr')[0].getName())
		except Exception, e:
			logging.error('Unable to get interface OIDs for ' +
				`target` + ': ' + `e`)
			return
		
		options = self.options.copy()
		options['host'] = target
		
		global Routes
		# analyze and gather monitored indices
		for index, oid in enumerate(oids):
			# check if this interface is to be monitored
			if oid[0][1] in config.Interfaces:
				try:
					# check active status
					if snmp_get(target, ifMib.importSymbols(
						'IF-MIB', 'ifAdminStatus')[0].getName() + (index + 1,))[0][1] != 1:
						raise Exception
				except:
					# inactive interface, or SNMP error
					logging.debug(target + ' interface ' + oid[0][1] +
						' is unavailable')
					continue
				
				# update global routing table
				Routes[target] = {
					'if_index': index +1,
					'if_name': oid[0][1]
				}
				# prepare to create worker thread
				options.update(Routes[target])
				
				logging.debug('Starting link poll thread for ' + `target` + 
					' ' + oid[0][1])
				t = LinkPollThread(options)
				ThreadPool.append(t)
				t.start()
				
		t = WeathermapThread(options)
		ThreadPool.append(t)
		t.start()

#------------------------------------------------------------------------------ 
class LinkPollThread(MonitorThread):
	"""
	Thread for monitoring a link's routing tables over a set period
	"""

	def __init__(self, options):
		super(LinkPollThread, self).__init__()
		self.func = self.loop_monitor
		self.interval = config.TrafficInterval
		self.if_index = options['if_index']
		self.if_name = options['if_name']
		self.target = options['host']
		
	def loop_monitor(self):
		"""
		Monitoring loop
		"""
		
		logging.debug('loop_monitor for ' + `self.target`)
		try:
			if not self.poll_routes():
				return
			if snmp_get(self.target,
				ifMib.importSymbols('IF-MIB', 'ifAdminStatus')[0].getName() +
					(self.if_index,))[0][1] != 1:
				logging.info(`self.target` + ' interface ' + self.if_name + ' is inactive')
				return
		except Exception, e:
			logging.debug('Could not check interface status: ' + `e`)
			return
		
		global Routes	# routing table store
		r = []			# temporary store
		
		for i, index in enumerate(self.ip_indices):
			if index[0][1] != self.if_index:
				continue
			if (self.ip_types[i][0][1] == 3 or self.ip_types[i][0][1] == 4
				or self.ip_masks[i] == '255.255.255.255'
				):
				logging.debug('Node ' + self.ip_routes[i] + ' is a neighbor')
				
				r.append(self.ip_routes[i])
		# update global store
		Routes[self.target]['routes'] = r
		
	def poll_routes(self):
		"""
		Update ip index and routing tables for node
		"""
		
		logging.debug('poll_route for ' + `self.target`)
		try:			
			# TODO: transition to GETBULK
			# Interface index for routing entries
			indices = snmp_walk(self.target,
				ifMib.importSymbols('RFC1213-MIB', 'ipRouteIfIndex')[0].getName())
			# Routing table destinations/IPs to neighbours
			routes = parse_routes(snmp_walk(self.target,
				ifMib.importSymbols('RFC1213-MIB', 'ipRouteDest')[0].getName()))
			# Route types
			types = snmp_walk(self.target,
				ifMib.importSymbols('RFC1213-MIB', 'ipRouteType')[0].getName())
			# Netmasks
			masks = parse_routes(snmp_walk(self.target,
				ifMib.importSymbols('RFC1213-MIB', 'ipRouteMask')[0].getName()))			
		except Exception, e:
			raise Exception, 'Could not poll routing tables for ' + \
				`self.target` + ': ' + `e`

		# test if routes and interface indexes are consistent
		if len(indices) != len(routes):
			logging.warning('Inconsistent routing tables and index for ' +
				`self.target` + '?')
			logging.debug('ipRoute Dump:\n' + str(routes) +
				'ipIndex Dump:\n' + str(indices))
			return False

		self.ip_indices, self.ip_routes, self.ip_types, self.ip_masks = \
			indices, routes, types, masks
		return True
		
class WeathermapThread(MonitorThread):
	
	def __init__(self, options):
		super(WeathermapThread, self).__init__()
		self.func = self.loop_weathermap
		self.interval = config.RefreshInterval
		self.options = options
		
	def loop_weathermap(self):
		from collections import deque
		from string import Template
		
		try:
			f = open(config.TopologyConf + '.template')
		except IOError:
			logging.debug('Could not find Weathermap conf template, aborting!')
			return	
		conf_template = f.read()
		f.close()
		
		# These are preselected locations. Only 4 nodes, anymore can't be shown..
		positions = deque(['75 360', '250 200', '425 360', '250 520'])	
		for node in config.Nodes:
			try:		
				conf_template += 'NODE MN' + node + '\n\tPOSITION ' + positions.pop() + \
					'\n\tLABEL Router_' + node + '\n\tICON $imgdir/icons/Safemesh1.png' + \
					'\n\tICONTPT 100\n\n'
			except IndexError:
				logging.error('FIXME: Ran out of node positions.')
				break
		conf_template = Template(conf_template).substitute(self.options)
			
		global Routes
		for node, table in Routes.items():
			logging.debug('Testing routes...')
			if not table.has_key('routes'):
				logging.warning('No routing entries for node ' + `node` + ' yet?')
				logging.debug('Dump:\n' + repr(table))
				continue
			logging.debug('Checking neighbor links for ' + `node`)
			for destination in table['routes']:
				#----------------------------
				# FIXME: hackity-hack
				#----------------------------
				if destination == '0.0.0.0':
					to = 'Handheld'
				elif destination == '192.168.0.0':
					to = 'Camera'
				elif destination == '255.255.255.0':
					to = 'Phone'
				else:
					# FIXME: link to correct nodes!
					from random import choice
					to = 'MN'+ choice(config.Nodes)
				#----------------------------
				logging.debug('Linking from ' + `node` + ' to ' + `to`)
				self.options['host'] = node
				self.options['if'] = table['if_name']
				conf_template += ('LINK MN' + node + '-' + table['if_name'] +
					'-' + to + '\n' +
					'\tNODES MN' + node + ' ' + to + '\n' +
					'\tTARGET ' + config.RrdTemplate.substitute(self.options) + '\n' +
					'\tINPOS 1\n' +
					'\tOUTPOS 2\n' +
					'\tUNIT bytes\n')
				if config.ShowBandwidth:
					conf_template += ('\tBANDWIDTH ' + `config.Bandwidth` +
						'\n\tDISPLAYVALUE 1\n')
				conf_template += '\tARROW normal\n\n'
		
		# write to config file
		f = open('weathermap.conf', 'w')
		print >> f, conf_template
		f.close()
		logging.debug('Weathermap configuration updated')
		
		# run Weathermap perl script
		# FIXME: Port this!
		os.system('./weathermap.pl')
		logging.debug(config.TopologyImg + ' updated')

def parse_routes(routes):
	"""
	Parse PySNMP routes into simple lists
	"""	
	from pysnmp.proto.rfc1155 import ipAddressPrettyOut
	return map(lambda r: ipAddressPrettyOut(r[0][1]), routes)	

#------------------------------------------------------------------------------
if __name__ == "__main__":
	LinkMon().main()