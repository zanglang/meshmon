__doc__ = """
Traffic Monitor for MeshMon
Version 0.1 - Jerry Chong <zanglang@gmail.com>

Based on meshtraffic.pl by Dirk Lessner, National ICT Australia
"""

from util import MonitorThread, ThreadPool
import config
import logging
import os
import random
import rrdtool
import snmp
import sys

if (config.Debug):
	logging.basicConfig(level=logging.DEBUG)

# OID index for each interface
ifIndices = {}

# pool instance
thread_pool = ThreadPool()

# Look up OIDs for in/out octets
InOctets = snmp.load_symbol('IF-MIB', 'ifInOctets')
OutOctets = snmp.load_symbol('IF-MIB', 'ifOutOctets')

#------------------------------------------------------------------------------ 	
class TrafficMon:
	
	def __init__(self):
		print 'TrafficMon started.\n' + \
			'Press <Ctrl>-C to shut down.'
		
		
	def destroy(self):
		""" Cleaning up """

		print 'Please wait while TrafficMon shuts down...'
		for thread in thread_pool.get():
			thread.run_flag = 0
			try: thread.join()
			except: pass
		logging.shutdown()
		sys.exit()

	def main(self):
		""" Main procedure """
		
		self.options = {
			'dir': config.RrdPath,
			'ext': config.ImgFormat.lower(),
			'imgdir': config.ImgPath,
			'int': config.GraphInterval
		}
		
		# configure rrdtool
		self.init_rrdtool()
		
		# initialize interface indices
		for node in config.Nodes:
			logging.debug('Initializing SNMP for ' + `node`)
			self.init_snmp(node)
		
#===============================================================================
#		num_threads = thread_pool.len() 
#		if num_threads > 0:
#			print str(num_threads), 'threads executing...'
#			while 1:
#				try:
#					input = raw_input()
#				except (EOFError, KeyboardInterrupt):
#					break;
#		else:
#			print 'Nothing to monitor.'
#		self.destroy()
#===============================================================================

	def init_rrdtool(self):
		""" RRDtool stuff """
		
		from os import path
		
		heartbeat = config.TrafficInterval * 2		
		options = self.options.copy()
		
		# configure rrdtool database
		for node in config.Nodes:			
			for interface in config.Interfaces:
				options['host'] = node
				options['if'] = interface
				rrd_file = config.RrdTemplate.substitute(options)
				
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
						logging.error('Unable to create RRDtool database!')
						sys.exit()
				else:
					print 'Using RRDtool database at ' + `rrd_file`

	def init_snmp(self, target):
		""" SNMP stuff """
		
		# SNMP GETBULK
		try:
			oids = snmp.walk(target, snmp.load_symbol('IF-MIB', 'ifDescr'))
		except Exception, e:
			logging.error('Unable to get interface OIDs for ' +
				`target` + ': ' + `e`)
			return
			
		options = self.options.copy()
		options['host'] = target
		
		# analyze and gather monitored indices
		for index, oid in enumerate(oids):
			# if this interface is to be monitored, fetch its index
			if oid[0][1] in config.Interfaces:
				options['if'] = oid[0][1]
				
				if not config.Simulate:
					logging.debug('Starting SNMP poll thread for ' + `target` + 
						' ' + oid[0][1])
					t1 = SnmpPollThread(
						(InOctets + (index + 1,),
							OutOctets + (index + 1,)),
						options
					)
				else:
					logging.debug('Starting simulator thread for ' + `target`)
					t1 = SimulationThread(options)
					
				thread_pool.add(t1)
				t1.start()
				
				logging.debug('Starting RRDtool graph thread')
				t2 = GraphingThread(options)
				thread_pool.add(t2)
				t2.start()

#------------------------------------------------------------------------------
 
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
 
class SnmpPollThread(MonitorThread):
	"""
	Thread for polling via SNMP over a set period
	"""

	def __init__(self, oids, options):
		super(SnmpPollThread, self).__init__()
		self.func = self.loop_snmp
		self.interval = config.TrafficInterval
		self.oids = oids
		self.rrd_file = config.RrdTemplate.substitute(options)
		self.target = options['host']
		
	def loop_snmp(self):
		""" SNMP polling loop """
		
		# FIXME: Warning - in/out Octets wrap back to 0. Is this handled properly?
		logging.debug('loop_snmp for ' + `self.target`)
		try:
			in_query, out_query = \
				snmp.get(self.target, self.oids[0]), \
				snmp.get(self.target, self.oids[1])
		except Exception, e:
			logging.error('Could not poll in/out octets for ' +
				`self.target` + ': ' + `e`)
			return
			
		if len(in_query) > 0 and len(out_query) > 0:
			in_octets = in_query[0][1]
			out_octets = out_query[0][1]
			
			logging.debug('Updating RRDtool in:' + str(in_octets) +
				' out:' + str(out_octets))
		
			# push results into rrdtool
			try:
				rrdtool.update(self.rrd_file,
					'-t',
					'in:out',
					'N:' + str(in_octets) + ':' + str(out_octets)
				)
			except rrdtool.error, e:
				logging.error(e)
			
#------------------------------------------------------------------------------ 
class GraphingThread(MonitorThread):
	"""
	Thread for refreshing RRDtool graph
	"""

	def __init__(self, options):
		super(GraphingThread, self).__init__()
		self.func = self.draw_graph
		self.interval = config.RefreshInterval		
		self.rrd_file = config.RrdTemplate.substitute(options)
		self.img_file = config.ImgTemplate.substitute(options)
		
		print 'Creating graph at ' + `self.img_file`
		
	def draw_graph(self):
		""" Draw RRDtool graph """

		logging.debug("draw_graph")
		headline = 'Router hourly graph (1 minute average)';
		maxline = ''
		# maxline = '#FF0000'
		try:
			from time import asctime
			rrdtool.graph(self.img_file,
				'-s -1' + config.GraphInterval,	# hour
				'-t', headline,
				'-h', '70',
				'-w', '350',
				'-a', config.ImgFormat,
				#'-l', '-20M',
				#'-u', '20M',
				#'--rigid',
				'-v', 'Bits/s',
				'DEF:inlast=' + self.rrd_file + ':in:LAST',
				'DEF:outlast=' + self.rrd_file + ':out:LAST',
				'DEF:inaverage=' + self.rrd_file + ':in:AVERAGE',
				'DEF:outaverage=' + self.rrd_file + ':out:AVERAGE',
				'DEF:inmax=' + self.rrd_file + ':in:MAX',
				'DEF:outmax=' + self.rrd_file + ':out:MAX',
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

#------------------------------------------------------------------------------ 

if __name__ == "__main__":
	mon = TrafficMon()
	mon.main()
	# If we have worker threads running...
	num_threads = thread_pool.len()
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