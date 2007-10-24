__doc__ = """
MeshMon data-gathering backend classes
Version 0.1 - Jerry Chong <zanglang@gmail.com>

Based on meshtraffic.pl by Dirk Lessner, National ICT Australia
"""

import logging, os, random, rrdtool
import aodv, config, nodes, snmp, threads

# Look up OIDs for in/out octets
InOctets = snmp.load_symbol('IF-MIB', 'ifInOctets')
OutOctets = snmp.load_symbol('IF-MIB', 'ifOutOctets')

# Used for simulation thread
random.seed()

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
			
			text = None
			############
			try:
				text = str(snmp.walk(target.address,
						(1,3,6,1,4,1,2021,8))[4][0][1])
			except Exception, e:
				logging.error('Unable to get AODV output for ' +
					`target.address` + ': ' + `e`)
				continue
			############
			aodv_entries = aodv.parse(text)
						
			for entry in aodv_entries:
				# check if it already exists
				dest = nodes.find(entry['destination'])
				
				if dest == None:
					# add newly discovered nodes to collection
					dest = nodes.create(entry['destination'])
					nodes.add(dest)
					
					try:
						print snmp.walk(dest.address,
							snmp.load_symbol('SNMPv2-MIB', 'sysDescr'))[0][0][1]
						# no problems here. this destination supports SNMP
						dest.type = nodes.ROUTER
						
					except Exception, e:
						if e.message == 'requestTimedOut':
							# assume machine does not have SNM
							# assume machine does not have SNMP?
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
						print snmp.walk(gateway.address,
							snmp.load_symbol('SNMPv2-MIB', 'sysDescr'))[0][0][1]
						# no problems here. this gateway supports SNMP
						gateway.type = nodes.ROUTER
						
					except Exception, e:
						if e.message == 'requestTimedOut':
							# assume machine does not have SNMP?
							gateway.type = nodes.GENERIC
						else:
							# we have a real error!
							logging.error(e)
						
				# add gateway as neighbouring node to target
				if not target.neighbours.has_key(gateway):
					target.neighbours[gateway] = []
				target.neighbours[gateway].append(entry['interface'])
				
				# add interfaces to node
				if entry['interface'] not in target.interfaces:
					target.interfaces.append(entry['interface'])

#-------------------------------------------------------------------------------
class GathererThread(threads.MonitorThread):
	""" Thread for polling via SNMP over a set period """

	def __init__(self, node):
		super(GathererThread, self).__init__()
		self.func = self.loop_snmp
		self.interval = config.TrafficInterval
		self.oids = []
		self.rrd_files = []
		self.target = node
		self.num_interfaces = 0
		self.refresh_interfaces()
		
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
				
				# add SNMP oids to be polled				oid_num = (InOctets + (oid[0][0][len(oid[0][0]) - 1],),
						OutOctets + (oid[0][0][len(oid[0][0]) - 1],))
						
				if not oid_num in self.oids:
					self.oids.append(oid_num)
				else:
					continue
					
				# add rrdtool files to be updated
				rrd_file = config.RrdTemplate.substitute({
					'dir': config.RrdPath,
					'host': self.target.address,
					'if': oid[0][1]
				})
				
				if rrd_file in self.rrd_files:
					continue
				
				if not os.path.exists(rrd_file):
					print 'Creating RRDtool database at ' + `rrd_file`
					try:
						rrdtool.create(rrd_file,
							#'-b now -60s',				# Start time now -1 min
							'-s ' + `config.TrafficInterval`,	# interval
							'DS:traffic_in:COUNTER:' + `config.TrafficInterval * 2` + ':0:3500000',
							'DS:traffic_out:COUNTER:' + `config.TrafficInterval * 2` + ':0:3500000',
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
				self.rrd_files.append(rrd_file)
				
		# record the interfaces used now for future reference
		self.num_interfaces = len(self.target.interfaces)
		
	def loop_snmp(self):
		""" SNMP polling loop """
		
		# has more interfaces been detected?
		if (self.target.interfaces > self.num_interfaces):
			self.refresh_interfaces()
		
		# FIXME: Warning - in/out Octets wrap back to 0. Is this handled properly?
		logging.debug('loop_snmp for ' + `self.target.address`)
		for index, oids in enumerate(self.oids):
			try:
				in_query, out_query = \
					snmp.get(self.target.address, oids[0]), \
					snmp.get(self.target.address, oids[1])
			except Exception, e:
				logging.error('Could not poll in/out octets for ' +
					`self.target.address` + ': ' + `e`)
				continue
			
			if len(in_query) > 0 and len(out_query) > 0:
				in_octets = in_query[0][1]
				out_octets = out_query[0][1]
				
				logging.debug('Updating RRDtool(' + str(index) +
					') in:' + str(in_octets) +
					' out:' + str(out_octets))
			
				# push results into rrdtool
				try:
					rrdtool.update(self.rrd_files[index],
						'-t',
						'traffic_in:traffic_out',
						'N:' + str(in_octets) + ':' + str(out_octets)
					)
				except Exception, e:
					logging.error(e)
					
#-------------------------------------------------------------------------------
class SimulationGathererThread(threads.MonitorThread):
	""" Thread for simulating traffic """
	
	def __init__(self, node):
		
		super(SimulationGathererThread, self).__init__()
		self.func = self.loop_simulate
		self.interval = config.TrafficInterval
		self.target = node
		self.rrd_files = []
		self.in_octets = {}
		self.out_octets = {}
		self.num_interfaces = 0
		self.refresh_interfaces()
		
	def refresh_interfaces(self):
		""" Initialize the RRDtool files depending on interfaces this node will use """
		
		for interface in self.target.interfaces:
			rrd_file = config.RrdTemplate.substitute({
				'dir': config.RrdPath,
				'host': self.target.address,
				'if': interface
			})
			
			if rrd_file in self.rrd_files:
				continue
			self.rrd_files.append(rrd_file)
			
		# record the interfaces used now for future reference
		self.num_interfaces = len(self.target.interfaces)
		
	def loop_simulate(self):
		""" Generate traffic loop """
		
		logging.debug('loop_simulate for ' + `self.target.address`)
		# has more interfaces been detected?
		if (self.target.interfaces > self.num_interfaces):
			self.refresh_interfaces()
		
		# 128 kbytes upstream/64 downstream
		for index, rrd_file in enumerate(self.rrd_files):
			
			if not self.in_octets.has_key(rrd_file):
				self.in_octets[rrd_file] = 0
			if not self.out_octets.has_key(rrd_file):
				self.out_octets[rrd_file] = 0
				
			self.in_octets[rrd_file] += random.randint(0, 131072)
			self.out_octets[rrd_file] += random.randint(0, 65536)
		
			logging.debug('Updating RRDtool in:' + str(self.in_octets[rrd_file]) +
				' out:' + str(self.out_octets[rrd_file]))
		
			# push the generated numbers into rrdtool
			try:
				rrdtool.update(rrd_file,
					'-t',
					'traffic_in:traffic_out',
					'N:' + str(self.in_octets[rrd_file]) +
						':' + str(self.out_octets[rrd_file])
				)
			except rrdtool.error, e:
				logging.error(e)
