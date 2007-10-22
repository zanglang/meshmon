__doc__ = """
MeshMon Weathermap/topology rendering class
Version 0.1 - Jerry Chong <zanglang@gmail.com>

Based on meshtraffic.pl by Dirk Lessner, National ICT Australia
"""

import gamin, os, subprocess
from string import Template
import config, logging, nodes, threads, topology

class WeathermapThread(threads.MonitorThread):
	
	def __init__(self):
		super(WeathermapThread, self).__init__()
		self.func = self.loop_weathermap
		self.interval = config.RefreshInterval
		# watch for changes in template
		self.mon = gamin.WatchMonitor()
		self.mon.watch_file(config.TopologyConf + '.template',
							self.refresh_template)
	
	def refresh_template(self, path=None, event=None):
		""" Template has changed, refresh configuration file """
		
		# GAMExists event triggers when we first start the thread
		# GAMChanged triggers when the template file gets updated
		# Note: if multiple updates were detected, Gamin will call this
		#	multiple times. This is somewhat expensive.
		if (event == gamin.GAMExists or event == gamin.GAMChanged):
			try:
				f = open(config.TopologyConf + '.template')
			except IOError:
				logging.error('Could not find Weathermap conf template, aborting!')
				return
			
			conf_template = f.read()
			f.close()
			
			# TODO: read widths and heights from topology
			
			
			# add known routers to weathermap nodes list
			for node in nodes.collection:
				position = str(node.position[0]) + ' ' + \
						str(node.position[1])
						
				conf_template += 'NODE MN' + node.address + '\n' + \
						'\tPOSITION ' + position + '\n' + \
						'\tLABEL Router_' + node.address + '\n' + \
						'\tICON $imgdir/icons/Safemesh1.png\n\n'
						# '\tICONTPT 100\n\n' # not required for PHP Weathermap
						
			conf_template = Template(conf_template).substitute({
				'dir': config.RrdPath,
				'ext': config.ImgFormat.lower(),
				'height': int(topology.height),
				'imgdir': config.ImgPath,
				'int': config.GraphInterval,
				'keypos': str(int(topology.width * 0.75)) + ' 15',
				'timepos': '290 520',
				'topologyimg': config.TopologyImg + '.tmp',
				'width': int(topology.width)
			})
			
			# add links to weathermap
			for node in nodes.collection:
				links = {}	# temporary links table
				
				# neighbour = adjacent gateway nodes
				# interface = interface last used to communicate with node
				for neighbour, interface in node.neighbours.items():
					
					### TODO: check if to and from are same node, check if
					### to and from were repeated
					if links.has_key(neighbour):
						links[neighbour] += 1
					else:
						links[neighbour] = 1
						
					#----------------------------
					logging.debug('Linking from ' + `node.address` +
								' to ' + `neighbour.address`)
					rrd_file = config.RrdTemplate.substitute({
						'dir': config.RrdPath,
						'host': node.address,
						'if': interface
					})
					
					# Is this a parallel link? 0 = first link, >=1 = parallel
					if links[neighbour] == 1:
						conf_template += (('LINK MN%s-%s-%s\n\t' +
								'NODES MN%s MN%s\n\t' +
								'TARGET %s\n\n') %
									(node.address, interface, neighbour.address,
									node.address, neighbour.address,
									rrd_file))
						
					else:
						# this is a parallel link. Calculate node offsets
						offsets = get_offsets(node.position, links[neighbour])
						offsets2 = get_offsets(neighbour.position, links[neighbour])
						conf_template += (('LINK MN%s-%s-%s-%d\n\t' +
								'NODES MN%s:%d:%d  MN%s:%d:%d\n\t' +
								'TARGET %s\n\n') % (
									node.address, interface,
									neighbour.address, links[neighbour],
									node.address, offsets[0], offsets[1]),
									neighbour.address, offsets2[0], offsets2[1],
									rrd_file)
									# we'll used straight lines for now
									#'\tVIA ' + position1 + '\n\n')

					#if config.ShowBandwidth:
					#	conf_template += ('\tBANDWIDTH ' + `config.Bandwidth` +
					#		'\n\tDISPLAYVALUE 1\n')
					# conf_template += '\tARROW normal\n\n'
					
			# write to config file
			f = open('weathermap.conf', 'w')
			try:
				print >> f, conf_template
			except:
				logging.error('Unable to save Weathermap conf template!')
				
			f.close()
			logging.debug('Weathermap configuration updated')
	
	def loop_weathermap(self):
		logging.debug('loop_weathermap')
		
		if self.mon.event_pending():
			self.mon.handle_events()
		else:
			# BUG: Temporary hack
			self.refresh_template(event=gamin.GAMExists)
		
		# run Weathermap perl script
		# Uncomment for Perl version -- needs compatible conf.template!
		# os.system('/usr/bin/weathermap4rrd -c weathermap.conf')
		#proc = subprocess.Popen(['php','weathermap/weathermap'])
		os.system('php weathermap/weathermap')
		#proc.wait()
		
		# copy over so we can solve flickering
		#proc2 = subprocess.Popen(['cp', config.TopologyImg + '.tmp',
				# config.TopologyImg])
		os.system('cp %s.tmp %s' % (config.TopologyImg, config.TopologyImg))
		#proc.wait()
		logging.debug(config.TopologyImg + ' updated')
		

def get_intermediate(node1, node2, offset):
	""" Calculate an intermediate position for VIA links
		:param offset: Offset factor to increase the distance of the positions"""
	
	logging.debug('Getting intermediate node for ' + str(node1) + ' ' + str(node2))
	
	x = (node1[0] + node2[0])/2
	y = (node1[1] + node2[1])/2
	
	if abs(node1[0] - node2[0]) <  abs(node1[1] - node2[1]):
		return (x - 20 * offset, y), (x + 20 * offset, y)
	else:
		return (x, y - 20 * offset), (x, y + 20 * offset)
	
def get_offsets(node, offset):
	""" Calculate an intermediate position for VIA links
		:param offset: Offset factor to increase the distance of the positions"""
		
	logging.debug('Getting node offsets for ' + str(node))
	
	return offset % 2 == 1 and (node[0] - 20 * offset, node[1] + 20 * offset) or \
			(node[0] + 20 * offset, node[1] - 20 * offset)
			
