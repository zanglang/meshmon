__doc__ = """
Traffic Monitor for MeshMon
Version 0.1 - Jerry Chong <zanglang@gmail.com>

Based on meshtraffic.pl by Dirk Lessner, National ICT Australia
"""

import logging, random, rrdtool, sys
import aodv, config, nodes, snmp, threads

if (config.Debug):
	logging.basicConfig(level=logging.DEBUG)

# OID index for each interface
ifIndices = {}

# Look up OIDs for in/out octets
InOctets = snmp.load_symbol('IF-MIB', 'ifInOctets')
OutOctets = snmp.load_symbol('IF-MIB', 'ifOutOctets')

# parameters for trafficmon
options = {
	'dir': config.RrdPath,
	'ext': config.ImgFormat.lower(),
	'int': config.GraphInterval,
	'heartbeat': config.TrafficInterval * 2
}

def main():
	""" Initialize monitoring """
	print 'TrafficMon started.\nPress <Ctrl>-C to shut down.'
	# initialize interface indices for monitored nodes
	for node in config.Nodes:
		logging.debug('Initializing node ' + `node`)
		if nodes.find(node):
			continue
		n = nodes.create(node)
		nodes.add(n)
		init_snmp(n)
	# start monitoring
	
def shutdown():
	""" Cleaning up """
	print 'Please wait while TrafficMon shuts down...'
	threads.terminate_all(wait=True)
	logging.shutdown()
	sys.exit()

def init_snmp(target):
	# TODO: GET AODV log here!
	############	
	text = None
	############
	
	aodv_entries = aodv.parse(text)
	for entry in aodv_entries:
		# check if it already exists
		dest = nodes.find(entry['destination'])
		if dest == None:
			# add newly discovered nodes to collection
			dest = nodes.create(entry['destination'])
			dest.type = nodes.ROUTER
			nodes.add(dest)
		else:
			# if a node was previously discovered but not identified
			if dest.type != nodes.ROUTER:
				dest.type = nodes.ROUTER
				
		# also check for AODV gateway nodes
		gateway = nodes.find(entry['gateway'])
		if gateway == None:
			gateway = nodes.create(entry['gateway'])
			gateway.type = nodes.ROUTER
			nodes.add(gateway)
		else:
			if gateway.type != nodes.ROUTER:
				gateway.type = nodes.ROUTER		
		
		# add interfaces to node
		if entry['interface'] not in target.interfaces:
			target.interfaces += entry['interface']
			
			###################
			# TODO: Run threads

#-----------------------------------------------------------------
class SnmpPollThread(MonitorThread):
	""" Thread for polling via SNMP over a set period """

	def __init__(self, node):
		super(SnmpPollThread, self).__init__()
		self.func = self.loop_snmp
		self.interval = config.TrafficInterval
		self.oids = []
		self.rrd_files = []
		self.target = node.address
		
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
					

class GraphingThread(MonitorThread):
	""" Thread for refreshing RRDtool graph """

	def __init__(self, node):
		super(GraphingThread, self).__init__()
		self.func = self.draw_graph
		self.interval = config.RefreshInterval
		
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
		
	def draw_graph(self):
		""" Draw RRDtool graph """

		from time import asctime
		logging.debug("draw_graph")
		headline = 'Router hourly graph (1 minute average)';
		maxline = ''
		# maxline = '#FF0000'
		for index, rrd_file in enumerate(self.rrd_files):
			try:
				rrdtool.graph(self.img_files[index],
					'-s -1' + config.GraphInterval,	# hour
					'-t', headline,
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
					'LINE1:outbitsinvmax' + maxline,
					'GPRINT:outbitslast:LAST:%5.1lf %sbps',
					'GPRINT:outbitsaverage:AVERAGE:%5.1lf %sbps',
					'GPRINT:outbitsmax:MAX:%5.1lf %sbps\\n',
					'COMMENT:  Last Updated.......\\: ' + asctime().replace(':','\\:')
				)
			except rrdtool.error, e:
				logging.error(e)
			
#-------------------------------			


		
	########################
	# Obsolete
	#vvvvvvvvvvvv
	
	# SNMP GETBULK

			if not config.Simulate:
				logging.debug('Starting SNMP poll thread for ' + `target` + 
					' ' + oid[0][1])
				threads.add(SnmpPollThread(
					(InOctets + (index + 1,),
						OutOctets + (index + 1,)),
					options
				))
			else:
				logging.debug('Starting simulator thread for ' + `target`)
				threads.add(SimulationThread(options))
			
			logging.debug('Starting RRDtool graph thread')
			threads.add(GraphingThread(options))
			
			
class SimulationThread(MonitorThread):
	"""
	Thread for simulating traffic in RRDtool
	"""
	
	def __init__(self, options):
		super(SimulationThread, self).__init__()
		self.func = self.loop_simulate
		self.interval = config.TrafficInterval
		self.rrd_file = config.RrdTemplate.substitute(options)
		self.target = options['host']
		self.in_octets = 0
		self.out_octets = 0
		random.seed()
		
	def loop_simulate(self):
		""" Generate traffic loop """
		
		logging.debug('loop_simulate for ' + `self.target`)
		# 128 kbytes upstream/64 downstream
		self.in_octets += random.randint(0, 131072)
		self.out_octets += random.randint(0, 65536)
		
		logging.debug('Updating RRDtool in:' + str(self.in_octets) +
			' out:' + str(self.out_octets))
	
		# push the generated numbers into rrdtool
		try:
			rrdtool.update(self.rrd_file,
				'-t',
				'in:out',
				'N:' + str(self.in_octets) + ':' + str(self.out_octets)
			)
		except rrdtool.error, e:
			logging.error(e)

#------------------------------------------------------------------------------ 

if __name__ == "__main__":
	mon = TrafficMon()
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