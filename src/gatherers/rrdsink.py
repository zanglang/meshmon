__doc__ = """
MeshMon data-gathering backend classes
Version 0.1 - Jerry Chong <zanglang@gmail.com>

Based on meshtraffic.pl by Dirk Lessner, National ICT Australia
"""

import logging, os, rrdtool
import aodv, config, nodes, snmp, threads, wifi
import rendering.rrd

# Look up OIDs for in/out octets
logging.debug('Loading SNMP symbols')
InOctets = snmp.load_symbol('IF-MIB', 'ifInOctets')
OutOctets = snmp.load_symbol('IF-MIB', 'ifOutOctets')

# cache for UCD-SNMP-MIB::ext*
execResults = {}

# cache for parsed AODV
aodvResults = {}


#-------------------------------------------------------------------------------
class AodvThread(threads.MonitorThread):
	""" Thread for checking AODV status """

	def __init__(self):
		super(AodvThread, self).__init__()
		self.func = self.loop_aodv
		self.interval = config.TrafficInterval

	def loop_aodv(self):

		for target in nodes.collection:

			# BUG: (maybe?) if a node does not have SNMP there's no way
			# to fetch its SNMP status
			if target.type != nodes.ROUTER:
				continue

			# first, reset neighbours list so we can redetect links
			target.neighbours = {}

			############
			text = None
			global execResults
			logging.debug('loop_aodv for %s' % target.address)
			
			try:
				execResults[target.address] = \
						snmp.walk(target.address, (1,3,6,1,4,1,2021,8))
				# try and increase interval
				if self.interval > 10:
					self.interval -= 1

			except Exception, e:
				logging.error('Unable to get AODV output for ' +
					`target.address` + ': ' + `e`)

				# try and reduce traffic interval
				if self.interval < 30:
					self.interval += 1
				continue

			target.aodv_data = \
					aodv.parse(str(execResults[target.address][8][0][1]))
			target.wifi_data = \
					wifi.parse(str(execResults[target.address][9][0][1]))

			for interface in target.aodv_data:
				# fetch entry for this link
				entry = target.aodv_data[interface]
				destaddress = entry['destination']

				# check if it already exists
				dest = nodes.find(destaddress)

				if dest == None:
					# add newly discovered nodes to collection
					dest = nodes.create(destaddress)
					nodes.add(dest)

					try:
						logging.debug(snmp.walk(dest.address,
								snmp.load_symbol('SNMPv2-MIB',
										'sysDescr'))[0][0][1])
						# no problems here. this destination supports SNMP
						dest.type = nodes.ROUTER

						logging.debug('Starting SNMP poll thread for ' + `dest.address`)
						threads.add(GathererThread(dest))

						logging.debug('Starting graphing thread for ' + `dest.address`)
						threads.add(rendering.rrd.GraphingThread(dest))

					except Exception, e:
						if e.message == 'requestTimedOut':
							# assume machine does not have SNM
							# assume machine does not have SNMP?
							logging.debug('PROBING %s has timed out!' % dest.address)
							dest.type = nodes.GENERIC
						else:
							# we have a real error!
							logging.error(e)


				# also check for AODV gateway nodes
				gateway = nodes.find(entry['gateway'])
				if gateway == None:
					gateway = nodes.create(entry['gateway'])
					nodes.add(gateway)

					try:
						logging.debug(snmp.walk(gateway.address,
								snmp.load_symbol('SNMPv2-MIB',
										'sysDescr'))[0][0][1])
						# no problems here. this gateway supports SNMP
						gateway.type = nodes.ROUTER

						logging.debug('Starting SNMP poll thread for ' + `gateway.address`)
						threads.add(GathererThread(gateway))

						logging.debug('Starting graphing thread for ' + `gateway.address`)
						threads.add(rendering.rrd.GraphingThread(gateway))

					except Exception, e:
						if e.message == 'requestTimedOut':
							# assume machine does not have SNMP?
							logging.debug('PROBING %s has timed out!' % gateway.address)
							gateway.type = nodes.GENERIC
						else:
							# we have a real error!
							logging.error(e)

				# add gateway as neighbouring node to target
				if not target.neighbours.has_key(gateway):
					target.neighbours[gateway] = []

				if interface not in target.neighbours[gateway]:
					target.neighbours[gateway].append(interface)

				# add interfaces to node
				if interface not in target.interfaces:
					target.interfaces.append(interface)


#-------------------------------------------------------------------------------
class GathererThread(threads.MonitorThread):
	""" Thread for polling via SNMP over a set period """

	def __init__(self, node):
		super(GathererThread, self).__init__()
		self.func = self.loop_snmp
		self.interval = config.TrafficInterval
		self.oids = {}

		# initialize node
		self.target = node
		self.target.rrd_files = {}
		self.num_interfaces = 0

		try:
			self.refresh_interfaces()
		except Exception, e:
			logging.debug('Could not initialize interfaces: %s. Try later?' % e)

	def refresh_interfaces(self):
		""" Initialize the SNMP OIDs to poll depending on interfaces this node will use """

		# check available network interfaces on host
		try:
			oids = snmp.walk(self.target.address,
					snmp.load_symbol('IF-MIB', 'ifDescr'))
			up = snmp.walk(self.target.address,
					snmp.load_symbol('IF-MIB', 'ifAdminStatus'))
		except Exception, e:
			logging.error('Unable to get interface OIDs for ' +
				`self.target.address` + ': ' + `e`)
			raise e

		# check which interfaces/indices are to be monitored
		for index, oid in enumerate(oids):

			if oid[0][1] in self.target.interfaces:

				# check if interface is online
				if up[index][0][1] != 1:
					continue

				# add SNMP oids to be polled
				oid_num = (InOctets + (oid[0][0][len(oid[0][0]) - 1],),
						OutOctets + (oid[0][0][len(oid[0][0]) - 1],))

				if oid_num not in self.oids.values():
					self.oids[oid[0][1]] = oid_num
				else:
					continue

				# add rrdtool files to be updated
				rrd_file = config.RrdTemplate.substitute({
					'dir': config.RrdPath,
					'host': self.target.address,
					'if': oid[0][1]
				})

				if rrd_file in self.target.rrd_files.values():
					continue

				# create RRDtool database if it doesn't exist
				if not os.path.exists(rrd_file):
					print 'Creating RRDtool database at ' + `rrd_file`
					try:
						rrdtool.create(rrd_file,
							#'-b now -60s',				# Start time now -1 min
							'-s ' + `config.TrafficInterval`,	# interval
							'DS:traffic_in:GAUGE:' + `config.TrafficInterval * 3` + ':U:U',
							'DS:traffic_out:GAUGE:' + `config.TrafficInterval * 3` + ':U:U',
							# wireless
							'DS:link:GAUGE:120:U:U',
							'DS:signal:GAUGE:120:U:U',
							'DS:noise:GAUGE:120:U:U',
							'RRA:LAST:0.1:1:720',		# 720 samples of 1 minute (12 hours)
							#'RRA:LAST:0.1:5:576',		# 576 samples of 5 minutes (48 hours)
							'RRA:AVERAGE:0.1:1:720',	# 720 samples of 1 minute (12 hours)
							#'RRA:AVERAGE:0.1:5:576',	# 576 samples of 5 minutes (48 hours)
							'RRA:MAX:0.1:1:720'			# 720 samples of 1 minute (12 hours)
							#'RRA:MAX:0.1:5:576'		# 576 samples of 5 minutes (48 hours)
						)
					except rrdtool.error, e:
						# this should be quite serious. Handle immediately!
						logging.error(e)
						raise Exception, 'Unable to create RRDtool database!'
				else:
					print 'Using RRDtool database at ' + `rrd_file`
				self.target.rrd_files[oid[0][1]] = rrd_file

		# record the interfaces used now for future reference
		self.num_interfaces = len(self.target.interfaces)


	def loop_snmp(self):
		""" SNMP polling loop """

		# has more interfaces been detected?
		try:
			if (self.target.interfaces > self.num_interfaces):
				self.refresh_interfaces()
		except Exception, e:
			logging.debug('Could not initialize interfaces: %s. Try later?' % e)

		logging.debug('loop_snmp for ' + `self.target.address`)

		# interate through known interfaces
		for interface in self.oids:

			in_octets = 0
			out_octets = 0
			
			if self.target.__dict__.has_key('aodv_data') and \
					self.target.aodv_data.has_key(interface):
				in_octets = int(self.target.aodv_data[interface]['received'])
				out_octets = int(self.target.aodv_data[interface]['sent'])
				
				if in_octets * 8 > config.Bandwidth:
					config.Bandwidth = in_octets * 8
					print 'Increasing max bandwidth to ', config.Bandwidth, \
							'bits/second'
				
				if out_octets * 8 > config.Bandwidth:
					config.Bandwidth = out_octets * 8
					print 'Increasing max bandwidth to ', config.Bandwidth, \
							'bits/second'
	
				# push results into rrdtool
				try:
					rrdtool.update(self.target.rrd_files[interface],
						'-t',
						'traffic_in:traffic_out',
						'N:%d:%d' % (in_octets, out_octets)
					)
					print ('Updating RRDtool in:%d out:%d' %
							(in_octets, out_octets))
				except Exception, e:
					logging.error(e)
					
			else:
				logging.debug('No AODV data yet?')
				
			# push wifi results also
			if self.target.__dict__.has_key('wifi_data') and \
					self.target.wifi_data.has_key(interface):
				try:
					rrdtool.update(self.target.rrd_files[interface],
						'-t',
						'link:signal:noise',
						'N:%d:%d:%d' % (self.target.wifi_data[interface]['link'] * 100,
								self.target.wifi_data[interface]['signal'] * 100,
								self.target.wifi_data[interface]['noise'] * 100)
					)
					print ('Updating RRDtool link:%d signal:%d noise:%d' %
							(self.target.wifi_data[interface]['link'],
							self.target.wifi_data[interface]['signal'],
							self.target.wifi_data[interface]['noise']))
				except Exception, e:
					logging.error(e)
					
			else:
				logging.debug('No wifi data yet?')
