__doc__ = """
Traffic Monitor for MeshMon
Version 0.1 - Jerry Chong <zanglang@gmail.com>

Based on meshtraffic.pl by Dirk Lessner, National ICT Australia
"""

from threading import Thread
import config
import logging
import rrdtool
import sys
import os

try:
	from pysnmp.entity.rfc3413.oneliner import cmdgen
	from pysnmp.smi import builder
except:
	print 'Python library PySNMP 4.x is required!'
	sys.exit()

if (config.Debug):
	logging.basicConfig(level=logging.DEBUG)

# OID index for each interface
ifIndices = {}
# pool for monitor and graph threads
ThreadPool = []

# create MIB builder and get object definitions
ifMib = builder.MibBuilder().loadModules('SNMPv2-MIB', 'IF-MIB')
# Look up OIDs for in/out octets
InOctets = ifMib.importSymbols('IF-MIB', 'ifInOctets')[0].getName()
OutOctets = ifMib.importSymbols('IF-MIB', 'ifOutOctets')[0].getName()

#------------------------------------------------------------------------------ 	
class TrafficMon:
	
	def __init__(self):		
		print 'TrafficMon started.\n' + \
			'Press <Ctrl>-C to shut down.'
		
		
	def destroy(self):
		""" Cleaning up """

		print 'Please wait while TrafficMon shuts down...'
		for thread in ThreadPool:
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
		
		if len(ThreadPool) > 0:
			print `len(ThreadPool)` + ' threads executing...'		
			while 1:
				try:
					input = raw_input()
				except (EOFError, KeyboardInterrupt):
					break;
		else:
			print 'Nothing to monitor.'
		self.destroy()

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
			oids = snmp_walk(target,
				ifMib.importSymbols('IF-MIB', 'ifDescr')[0].getName())
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
				
				logging.debug('Starting SNMP poll thread for ' + `target` + 
					' ' + oid[0][1])
				t1 = SnmpPollThread(
					(InOctets + (index + 1,),
						OutOctets + (index + 1,)),
					options
				)
				ThreadPool.append(t1)
				t1.start()
				
				logging.debug('Starting RRDtool graph thread')
				t2 = GraphingThread(options)
				ThreadPool.append(t2)
				t2.start()

#------------------------------------------------------------------------------ 
class MonitorThread(Thread):
	"""
	Thread super-class
	"""
	def __init__(self):
		super(MonitorThread, self).__init__()
		self.interval = 60	# dummy interval
		self.func = self.__dummy_func
		self.run_flag = 1
		
	def run(self):
		from traceback import print_exc
		from time import sleep
		try:
			while self.run_flag == 1:
				self.func()
				sleep(self.interval)
		except Exception, e:
			print_exc()
			print 'Thread stopped abnormally'
			pass
		
	def __dummy_func(self):
		print 'noop'

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
		
		logging.debug('loop_snmp for ' + `self.target`)
		try:
			in_query, out_query = \
				snmp_get(self.target, self.oids[0]), \
				snmp_get(self.target, self.oids[1])
		except Exception, e:
			raise Exception, 'Could not poll in/out octets for ' + \
				`self.target` + ': ' + `e`
			
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

def snmp_walk(target, objects):
	""" SNMP WALK """
	errorIndication, errorStatus, errorIndex, varBinds = \
			cmdgen.CommandGenerator().nextCmd(
		cmdgen.CommunityData('my-agent', config.Community, 0),
		cmdgen.UdpTransportTarget((target, 161)),
		objects
	)
	if (errorIndication != None):
		raise Exception, errorIndication
	# print errorStatus
	# print errorIndex
	return varBinds;
	
def snmp_get(target, objects):
	""" SNMP GET query """
	errorIndication, errorStatus, errorIndex, varBinds = \
			cmdgen.CommandGenerator().getCmd(
		cmdgen.CommunityData('my-agent', config.Community, 0),
		cmdgen.UdpTransportTarget((target, 161)),
		objects
	)
	if (errorIndication != None):
		raise Exception, errorIndication
	# print errorStatus
	# print errorIndex
	return varBinds;

def snmp_bulk_get(target, objects, nonRepeaters = 0, maxRepetitions = 10):
	""" SNMP GET query """
	errorIndication, errorStatus, errorIndex, varBinds = \
			cmdgen.CommandGenerator().bulkCmd(
		cmdgen.CommunityData('my-agent', config.Community, 0),
		cmdgen.UdpTransportTarget((target, 161)),
		nonRepeaters,
		maxRepetitions,
		*objects
	)
	if (errorIndication != None):
		raise Exception, errorIndication
	# print errorStatus
	# print errorIndex
	return varBinds;

#------------------------------------------------------------------------------ 

if __name__ == "__main__":
	TrafficMon().main()