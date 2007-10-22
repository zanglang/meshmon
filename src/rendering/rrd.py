__doc__ = """
MeshMon rendering backend classes
Version 0.1 - Jerry Chong <zanglang@gmail.com>

Based on meshtraffic.pl by Dirk Lessner, National ICT Australia
"""

import logging, os, rrdtool
import config, threads


class GraphingThread(threads.MonitorThread):
	""" Thread for refreshing RRDtool graph """

	def __init__(self, node):
		super(GraphingThread, self).__init__()
		self.func = self.draw_graph
		self.interval = config.RefreshInterval
		self.rrd_files = []
		self.img_files = []
		self.node = node
		self.num_interfaces = 0
		self.refresh_interfaces()
		
	def refresh_interfaces(self):
		""" Initialize the RRDtool images depending on interfaces this node will use """
		
		for interface in self.node.interfaces:
			rrd_file = config.RrdTemplate.substitute({
				'dir': config.RrdPath,
				'host': self.node.address,
				'if': interface
			})
			
			if rrd_file in self.rrd_files:
				continue
			self.rrd_files.append(rrd_file)
			
			img = config.ImgTemplate.substitute({
				'imgdir': config.ImgPath,
				'host': self.node.address,
				'if': interface,
				'ext': config.ImgFormat.lower()
			})
			
			self.img_files.append(img)
			print 'Creating graph at ' + `img`
			
		# record the interfaces used now for future reference
		self.num_interfaces = len(self.node.interfaces)
		
	def draw_graph(self):
		""" Draw RRDtool graph """

		from time import asctime
		logging.debug("draw_graph")
		
		# has more interfaces been detected?
		if (self.node.interfaces > self.num_interfaces):
			self.refresh_interfaces()
		
		for index, rrd_file in enumerate(self.rrd_files):
			if not os.path.exists(rrd_file):
				logging.error('RRD file %s does not exist?' % rrd_file)
				continue
			
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
					'LINE1:inbitsmax#FF0000',
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