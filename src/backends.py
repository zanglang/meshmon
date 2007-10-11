__doc__ = """
MeshMon backend implementation classes
Version 0.1 - Jerry Chong <zanglang@gmail.com>

Based on meshtraffic.pl by Dirk Lessner, National ICT Australia
"""

import logging, path, random, rrdtool
import config, snmp

# Look up OIDs for in/out octets
InOctets = snmp.load_symbol('IF-MIB', 'ifInOctets')
OutOctets = snmp.load_symbol('IF-MIB', 'ifOutOctets')

# Used for simulation thread
random.seed()

class GraphingThread(MonitorThread):
	""" Thread for refreshing RRDtool graph """

	def __init__(self, node):
		super(GraphingThread, self).__init__()
		self.func = self.draw_graph
		self.interval = config.RefreshInterval
		self.rrd_files = []
		self.img_files = []
		self.num_interfaces = 0
		self.refresh_interfaces()
		
	def refresh_interfaces(self):
		""" Initialize the RRDtool images depending on interfaces this node will use """
		for interface in node.interfaces:
			self.rrd_files.append(config.RrdTemplate.substitute({
				'dir': config.RrdPath,
				'host': node.address,
				'if': interface
			}))
			img = config.ImgTemplate.substitute({
				'imgdir': config.ImgPath,
				'host': node.address,
				'if': interface,
				'ext': config.ImgFormat.lower()
			})
			self.img_files.append(img)
			print 'Creating graph at ' + `img`
			
		# record the interfaces used now for future reference
		self.num_interfaces = len(node.interfaces)
		
	def draw_graph(self):
		""" Draw RRDtool graph """

		from time import asctime
		logging.debug("draw_graph")
		
		# has more interfaces been detected?
		if (node.interfaces > self.num_interfaces)
			self.refresh_interfaces()
		
		for index, rrd_file in enumerate(self.rrd_files):
			try:
				rrdtool.graph(self.img_files[index],
					'-s -1' + config.GraphInterval,	# hour
					'-t', 'Router hourly graph (1 minute average)',
					'-h', '70',
					'-w', '350',
					'-a', config.ImgFormat,
					#'-l', '-20M',
					#'-u', '20M',
					#'--rigid',
					'-v', 'Bits/s',
					'DEF:inlast=' + rrd_file + ':in:LAST',
					'DEF:outlast=' + rrd_file + ':out:LAST',
					'DEF:inaverage=' + rrd_file + ':in:AVERAGE',
					'DEF:outaverage=' + rrd_file + ':out:AVERAGE',
					'DEF:inmax=' + rrd_file + ':in:MAX',
					'DEF:outmax=' + rrd_file + ':out:MAX',
					'CDEF:inbitslast=inlast,8,*',
					'CDEF:inbitsaverage=inaverage,8,*',
					'CDEF:inbitsmax=inmax,8,*',
					'CDEF:outbitslast=outlast,8,*',
					'CDEF:outbitsaverage=outaverage,8,*',
					'CDEF:outbitsmax=outmax,8,*',
					'CDEF:outbitsinvlast=outbitslast,-1,*',
					'CDEF:outbitsinvaverage=outbitsaverage,-1,*',
					'CDEF:outbitsinvmax=outbitsmax,-1,*',
					'AREA:inbitsaverage#0000FF:In (last/avg/max)..\\:',
					'LINE1:inbitsmax' + maxline,
					'GPRINT:inbitslast:LAST:%5.1lf %sbps',
					'GPRINT:inbitsaverage:AVERAGE:%5.1lf %sbps',
					'GPRINT:inbitsmax:MAX:%5.1lf %sbps\\n',
					'AREA:outbitsinvaverage#00FF00:Out (last/avg/max).\\:',
					#'LINE1:outbitsinvmax#FF0000',	# set colour of highest watermark
					'LINE1:outbitsinvmax',
					'GPRINT:outbitslast:LAST:%5.1lf %sbps',
					'GPRINT:outbitsaverage:AVERAGE:%5.1lf %sbps',
					'GPRINT:outbitsmax:MAX:%5.1lf %sbps\\n',
					'COMMENT:  Last Updated.......\\: ' + asctime().replace(':','\\:')
				)
			except rrdtool.error, e:
				logging.error(e)

#--------------------------------------------------------
class SnmpPollThread(MonitorThread):
	""" Thread for polling via SNMP over a set period """

	def __init__(self, node):
		super(SnmpPollThread, self).__init__()
		self.func = self.loop_snmp
		self.interval = config.TrafficInterval
		self.oids = []
		self.rrd_files = []
		self.target = node.address
		self.num_interfaces = 0
		self.refresh_interfaces()
		
	def refresh_interfaces(self):
		""" Initialize the SNMP OIDs to poll depending on interfaces this node will use """
		
		# check available network interfaces on host
		try:
			oids = snmp.walk(target, snmp.load_symbol('IF-MIB', 'ifDescr'))
		except Exception, e:
			logging.error('Unable to get interface OIDs for ' +
				`target` + ': ' + `e`)
			raise e
		
		# check which interfaces/indices are to be monitored
		for index, oid in enumerate(oids):
			if oid[0][1] in node.interfaces:
				# add SNMP oids to be polled
				self.oids.append((InOctets + (index + 1,),
						OutOctets + (index + 1,)))
				# add rrdtool files to be updated
				rrd_file = config.RrdTemplate.substitute({
					'dir': config.RrdPath,
					'host': node.address,
					'if': oid[0][1]
				}))
				
				if not path.exists(rrd_file):
					print 'Creating RRDtool database at ' + `rrd_file`
					try:
						rrdtool.create(rrd_file,
							#'-b now -60s',				# Start time now -1 min
							'-s ' + `config.TrafficInterval`,	# interval
							'DS:in:COUNTER:' + `heartbeat` + ':0:3500000',
							'DS:out:COUNTER:' + `heartbeat` + ':0:3500000',
							'RRA:LAST:0.1:1:720',		# 720 samples of 1 minute (12 hours)
							#'RRA:LAST:0.1:5:576',		# 576 samples of 5 minutes (48 hours)
							'RRA:AVERAGE:0.1:1:720',	# 720 samples of 1 minute (12 hours)
							#'RRA:AVERAGE:0.1:5:576',	# 576 samples of 5 minutes (48 hours)
							'RRA:MAX:0.1:1:720'			# 720 samples of 1 minute (12 hours)
							#'RRA:MAX:0.1:5:576'		# 576 samples of 5 minutes (48 hours)
						)
					except:
						# this should be quite serious. Handle immediately!
						raise Exception, 'Unable to create RRDtool database!'
				else:
					print 'Using RRDtool database at ' + `rrd_file`
				self.rrd_files.append(rrd_file)
				
		# record the interfaces used now for future reference
		self.num_interfaces = len(node.interfaces)
		
	def loop_snmp(self):
		""" SNMP polling loop """
		
		# FIXME: Warning - in/out Octets wrap back to 0. Is this handled properly?
		logging.debug('loop_snmp for ' + `self.target`)
		for index, oids in enumerate(self.oids):
			try:
				in_query, out_query = \
					snmp.get(self.target, oids[0]), \
					snmp.get(self.target, oids[1])
			except Exception, e:
				logging.error('Could not poll in/out octets for ' +
					`self.target` + ': ' + `e`)
				continue
			
			if len(in_query) > 0 and len(out_query) > 0:
				in_octets = in_query[0][1]
				out_octets = out_query[0][1]
				
				logging.debug('Updating RRDtool in:' + str(in_octets) +
					' out:' + str(out_octets))
			
				# push results into rrdtool
				try:
					rrdtool.update(self.rrd_files[index],
						'-t',
						'in:out',
						'N:' + str(in_octets) + ':' + str(out_octets)
					)
				except rrdtool.error, e:
					logging.error(e)
					
#-----------------------------------
class SimulationPollThread(MonitorThread):
	""" Thread for simulating traffic """
	
	def __init__(self, node):
		super(SimulationThread, self).__init__()
		self.func = self.loop_simulate
		self.interval = config.TrafficInterval
		self.target = node.address
		self.in_octets = {}
		self.out_octets = {}
		self.num_interfaces = 0
		self.refresh_interfaces()
		
	def refresh_interfaces(self):
		""" Initialize the RRDtool files depending on interfaces this node will use """
		for interface in node.interfaces:
			self.rrd_files.append(config.RrdTemplate.substitute({
				'dir': config.RrdPath,
				'host': node.address,
				'if': interface
			}))
			
		# record the interfaces used now for future reference
		self.num_interfaces = len(node.interfaces)
		
	def loop_simulate(self):
		""" Generate traffic loop """
		
		logging.debug('loop_simulate for ' + `self.target`)
		# has more interfaces been detected?
		if (node.interfaces > self.num_interfaces)
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
					'in:out',
					'N:' + str(self.in_octets[rrd_file]) +
						':' + str(self.out_octets[rrd_file])
				)
			except rrdtool.error, e:
				logging.error(e)