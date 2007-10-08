#!/usr/bin/env python2.5

__doc__ = """
Link Monitor for MeshMon
Version 0.1 - Jerry Chong <zanglang@gmail.com>

Based on meshmon.pl by Dirk Lessner, National ICT Australia
"""

import logging, os, sys
from collections import deque
from time import sleep
import aodv, config, snmp, threads

if (config.Debug):
	logging.basicConfig(level=logging.DEBUG)

# global routing table store
routes = {}

# BUG: These are preselected locations. Only 4 nodes, anymore can't be shown..
# positions = deque(['75 360', '250 200', '425 360', '250 520'])
# TODO: read this and 'via' paths from a file so we can get a perfect graph
positions = deque([(400,260), (100,260), (250,260)])
#positions = deque([(350,460),(150,460), (250,60), (250,260)])

# node positions temporary store
node_positions = {}

# some predefined nodes
#camera = (250,60)
#handheld = (150,460)
#phone = (350,460)
camera = (80,260)
handheld = (420,260)
phone = (420,460)

#------------------------------------------------------------------------------ 
class LinkMon:
	
	def __init__(self):
		print 'LinkMon started.\n' + \
			'Press <Ctrl>-C to shut down.'
			
	def destroy(self):
		""" Cleaning up """
		
		print 'Please wait while LinkMon shuts down...'
		# stop worker threads
		threads.terminate_all(wait=True)
		logging.shutdown()
		sys.exit()
		
	def main(self):
		""" Main procedure """
		
		self.options = {
			'dir': config.RrdPath,
			'ext': config.ImgFormat.lower(),
			'imgdir': config.ImgPath,
			'int': config.GraphInterval,
			'topologyimg': config.TopologyImg + '.tmp'
		}
		
		global routes
		# initialize each monitored node
		for node in config.Nodes:
			logging.debug('Initializing WLAN interfaces for ' + `node`)
			# initialize stores
			routes[node] = {}
			# initialize coordinates
			try:
				node_positions[node] = positions.pop()
				logging.debug('Node ' + node + ' assigned to ' + str(node_positions[node]))
			except IndexError:
				logging.error('FIXME: Ran out of node positions.')
				node_positions[node] = (0,0)
			
		for node in config.Nodes:
			# initialize monitoring interfaces
			self.init_interfaces(node)
		
	def init_interfaces(self, target):
		""" Check target node interfaces """
		
		# SNMP GET
		try:
			oids = snmp.walk(target, snmp.load_symbol('IF-MIB', 'ifDescr'))
		except Exception, e:
			logging.error('Unable to get interface OIDs for ' +
				`target` + ': ' + `e`)
			return
		
		options = self.options.copy()
		options['host'] = target
		
		global routes
		# analyze and gather monitored indices
		for index, oid in enumerate(oids):
			# check if this interface is to be monitored
			if oid[0][1] in config.Interfaces:
				try:
					# check active status
					if snmp.get(target,
						snmp.load_symbol('IF-MIB', 'ifAdminStatus') +
							(index + 1,))[0][1] != 1:
						raise Exception
				except Exception, e:
					# inactive interface, or SNMP error
					logging.debug(target + ' interface ' + oid[0][1] +
						' is unavailable: ' + str(e))
					continue
				
				# update global routing table
				# BUG: we forgot to separate interfaces!!
				routes[target] = {
					'if_index': index +1,
					'if_name': oid[0][1]
				}
				# prepare to create worker thread
				options.update(routes[target])
				
				logging.debug('Starting link poll thread for ' + `target` + 
					' ' + oid[0][1])
				threads.add(LinkPollThread(options))
		
		logging.debug('Starting Weathermap thread')		
		threads.add(WeathermapThread(options))

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
		while 1:
			try:
				if not self.poll_routes():
					return
				if snmp.get(self.target,
					snmp.load_symbol('IF-MIB', 'ifAdminStatus') +
						(self.if_index,))[0][1] != 1:
					logging.info(`self.target` + ' interface ' + self.if_name + ' is inactive')
					sleep(5)
					continue
				break
			except Exception, e:
				logging.debug('Could not check interface status: ' + `e`)
				sleep(5)
				continue
		
		global routes	# routing table store
		r = []			# temporary store
		
		for i, index in enumerate(self.ip_indices):
			if index[0][1] != self.if_index:
				continue
			if (self.ip_types[i][0][1] == 3 or
					self.ip_types[i][0][1] == 4 or
					self.ip_masks[i] == '255.255.255.255'):
				logging.debug('Node ' + self.ip_routes[i] + ' is a neighbor')				
				r.append(self.ip_routes[i])
		# update global store
		routes[self.target]['routes'] = r
		
	def poll_routes(self):
		"""
		Update ip index and routing tables for node
		"""
		
		logging.debug('poll_route for ' + `self.target`)
		try:			
			# TODO: transition to GETBULK
			# TODO: 'Simulate' support
			# Interface index for routing entries
			indices = snmp.walk(self.target,
				snmp.load_symbol('RFC1213-MIB', 'ipRouteIfIndex'))
			# Routing table destinations/IPs to neighbours
			routes = parse_routes(snmp.walk(self.target,
				snmp.load_symbol('RFC1213-MIB', 'ipRouteDest')))
			# Route types
			types = snmp.walk(self.target,
				snmp.load_symbol('RFC1213-MIB', 'ipRouteType'))
			# Netmasks
			masks = parse_routes(snmp.walk(self.target,
				snmp.load_symbol('RFC1213-MIB', 'ipRouteMask')))
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
		from string import Template
		
		logging.debug('loop_weathermap')
		
		# TODO: use Gamin to monitor template changes instead of reloading
		try:
			f = open(config.TopologyConf + '.template')
		except IOError:
			logging.debug('Could not find Weathermap conf template, aborting!')
			return
		conf_template = f.read()
		f.close()
		
		for node in config.Nodes:
			position = str(node_positions[node][0]) + ' ' + \
					str(node_positions[node][1])
			conf_template += 'NODE MN' + node + '\n' + \
					'\tPOSITION ' + position + '\n' + \
					'\tLABEL Router_' + node + '\n' + \
					'\tICON $imgdir/icons/Safemesh1.png\n\n'
					# '\tICONTPT 100\n\n' # not required for PHP Weathermap
		conf_template = Template(conf_template).substitute(self.options)
		
		global routes
		for node, table in routes.items():
			logging.debug('Testing routes...')
			if not table.has_key('routes'):
				logging.warning('No routing entries for node ' + `node` + ' yet?')
				logging.debug('Dump:\n' + repr(table))
				continue
			logging.debug('Checking neighbor links for ' + `node`)
			for destination in table['routes']:
				# FIXME: hackity-hack
				# TODO: Fix to multi-route algorithm
				logging.debug('Checking destination ' + destination)
				if destination == '10.0.0.0':
					to = 'Handheld'
					dst_node = handheld
				#elif destination == '10.0.0.0':
				#	to = 'Camera'
				#	dst_node = camera
				#elif destination == '255.255.255.0':
				#	to = 'Phone'
				#	dst_node = phone
				#elif destination in ('0.0.0.0','192.168.0.0','255.255.255.0',
				#		'10.0.0.0','10.0.1.0'):
				#	continue
				elif destination in config.Nodes and destination != node:
					to = 'MN' + destination
					dst_node = node_positions[destination]
				else:
					logging.debug("Unrecorded node: " + destination)
					if len(config.Nodes) <= 1:
						continue
					# FIXME: link to correct nodes!
					from random import choice
					while 1:
						choice_node = choice(config.Nodes)
						if choice_node is node:
							continue
						to = 'MN'+ choice_node
						dst_node = node_positions[choice_node]
						break
				
				# calculate intermediate path
				via1, via2 = get_intermediate(node_positions[node], dst_node)
				position1 = str(via1[0]) + ' ' + str(via1[1])
				position2 = str(via2[0]) + ' ' + str(via2[1])	
				
				#----------------------------
				logging.debug('Linking from ' + `node` + ' to ' + `to`)
				self.options['host'] = node
				self.options['if'] = table['if_name']
				conf_template += ('LINK MN' + node + '-' + table['if_name'] +
					'-' + to + '\n' +
					'\tNODES MN' + node + ' ' + to + '\n' +
					'\tTARGET ' + config.RrdTemplate.substitute(self.options) +
					'\n\n')
				conf_template += ('LINK MN' + node + '-' + table['if_name'] +
					'-' + to + '-1\n' +
					'\tNODES MN' + node + ' ' + to + '\n' +
					'\tVIA ' + position1 + '\n\n')
				conf_template += ('LINK MN' + node + '-' + table['if_name'] +
					'-' + to + '-2\n' +
					'\tNODES MN' + node + ' ' + to + '\n' +
					'\tVIA ' + position2 + '\n\n')
			# This portion is unsupported by PHP Weathermap
					#'\tINPOS 1\n' +
					#'\tOUTPOS 2\n' +
					#'\tUNIT bytes\n')
				#if config.ShowBandwidth:
				#	conf_template += ('\tBANDWIDTH ' + `config.Bandwidth` +
				#		'\n\tDISPLAYVALUE 1\n')
				# conf_template += '\tARROW normal\n\n'
		
		# write to config file
		f = open('weathermap.conf', 'w')
		print >> f, conf_template
		f.close()
		logging.debug('Weathermap configuration updated')
		
		# run Weathermap perl script
		# Uncomment for Perl version -- needs compatible conf.template!
		# os.system('/usr/bin/weathermap4rrd -c weathermap.conf')
		os.system('php weathermap/weathermap')
		# copy over so we can solve flickering
		os.system('cp %s.tmp %s' % (config.TopologyImg, config.TopologyImg))
		logging.debug(config.TopologyImg + ' updated')

def get_intermediate(node1, node2):
	logging.debug('Getting intermediate node for ' + str(node1) + ' ' + str(node2))
	x = (node1[0] + node2[0])/2
	y = (node1[1] + node2[1])/2
	if abs(node1[0] - node2[0]) <  abs(node1[1] - node2[1]):
		return (x - 40, y), (x + 40, y)
	else:
		return (x, y - 40), (x, y + 40)

def parse_routes(routes):
	"""
	Parse PySNMP routes into simple lists
	"""	
	from pysnmp.proto.rfc1155 import ipAddressPrettyOut
	return map(lambda r: ipAddressPrettyOut(r[0][1]), routes)	

#------------------------------------------------------------------------------
if __name__ == "__main__":
	mon = LinkMon()
	mon.main()
	# If we have worker threads running...
	num_threads = threads.len()
	if num_threads > 0:
		print str(num_threads), 'threads executing...'
		while 1:
			try:
				input = raw_input()
			except (EOFError, KeyboardInterrupt):
				break
	else:
		# no threads running at all! (possibly bad configuration)
		print 'Nothing to monitor.'
	mon.destroy()