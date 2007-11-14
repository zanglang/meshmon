__doc__ = """
MeshMon Weathermap/topology rendering class
Version 0.1 - Jerry Chong <zanglang@gmail.com>

Based on meshtraffic.pl by Dirk Lessner, National ICT Australia
"""

import gamin, os
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
		#
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

			# add known routers to weathermap nodes list
			for node in nodes.collection:
				position = str(node.position[0]) + ' ' + \
						str(node.position[1])

				conf_template += ('NODE MN%s\n' +
						'\tPOSITION %s\n' +
						'\tLABEL %s\n' +
						'\tICON $imgdir/icons/%s\n\n') % \
								(node.address, str(position), node.address,
								(node.type == nodes.ROUTER
										and 'Safemesh1.png'
										or 'terminal.png'))

			conf_template = Template(conf_template).substitute({
				'dir': config.RrdPath,
				'ext': config.ImgFormat.lower(),
				'height': int(topology.height),
				'imgdir': config.ImgPath,
				'int': config.GraphInterval,
				'keypos': str(topology.width - 130) + ' 15',
				'timepos': str(topology.width - 210) + ' ' + str(topology.height - 5),
				'topologyimg': config.TopologyImg + '.tmp',
				'width': int(topology.width)
			})

			# add links to weathermap
			for node in nodes.collection:
				links = {}	# temporary links table

				# neighbour = adjacent gateway nodes
				# interface = interface last used to communicate with node
				for neighbour, interfaces in node.neighbours.items():
					for interface in interfaces:

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
									'TARGET %s\n') %
										(node.address, interface, neighbour.address,
										node.address, neighbour.address,
										rrd_file))

						else:
							# this is a parallel link. Calculate node offsets
							#offsets = get_offsets(node.position, links[neighbour])
							#offsets2 = get_offsets(neighbour.position, links[neighbour])
							position = get_intermediate(node.position, neighbour.position, links[neighbour])

							conf_template += (('LINK MN%s-%s-%s-%d\n\t' +
									#'NODES MN%s:%d:%d  MN%s:%d:%d\n\t' +
									'NODES MN%s MN%s\n\t' +
									'TARGET %s\n' +
									'\tVIA %d %d\n') % (
										node.address, interface,
										neighbour.address, links[neighbour],
										#node.address, offsets[0], offsets[1],
										#neighbour.address, offsets2[0], offsets2[1],
										node.address, neighbour.address,
										rrd_file,
										position[0], position[1]
										))
										# we'll used straight lines for now
										#'\tVIA ' + position1 + '\n')

						if config.ShowBandwidthLabel == 'interface':
							conf_template += ('\tBWLABEL none\n')
							conf_template += ('\tOUTCOMMENT %s\n' % interface)
							conf_template += ('\tCOMMENTPOS 70 30\n')
							conf_template += ('\tCOMMENTFONT 2\n')
						else:
							conf_template += ('\tBWLABEL %s\n' %
									config.ShowBandwidthLabel)
							conf_template += ('\tBWLABELPOS 70 30\n')

						conf_template += ('\tBANDWIDTH %d\n' % config.Bandwidth)
						conf_template += ('\tOVERLIBGRAPH images/%s\n' %
								rrd_file.replace('.rrd', '.' +
								config.ImgFormat.lower()))

						conf_template += ('\n')

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

		os.system('php weathermap/weathermap')
		os.system('cp %s.tmp %s' % (config.TopologyImg, config.TopologyImg))
		logging.debug(config.TopologyImg + ' updated')



def get_intermediate(node1, node2, offset):
	""" Calculate an intermediate position for VIA links
		:param offset: Offset factor to increase the distance of the positions"""

	logging.debug('Getting intermediate node for ' + str(node1) + ' ' + str(node2))

	if node1[0] == node2[0]:
		x = node1[0]
		y = abs(node1[1] - node2[1])/2 + min(node1[1], node2[1])
		return offset % 2 == 1 and (x - 20 * offset, y) or (x + 20 * offset, y)

	if node1[1] == node2[1]:
		y = node1[1]
		x = abs(node1[0] - node2[0])/2 + min(node1[0], node2[0])
		return offset % 2 == 1 and (x, y - 20 * offset) or (x, y + 20 * offset)

	x = abs(node1[0] - node2[0])/2 + min(node1[0], node2[0])
	y = abs(node1[1] - node2[1])/2 + min(node1[1], node2[1])

	logging.debug('Intermediate: ' + str(x) + ' ' + str(y))
	result = offset % 2 == 1 \
			and (x - 20 * offset, y - 20 * offset) \
			or (x + 20 * offset , y + 20 * offset)
	logging.debug('Result: ' + str(result))
	return result



def get_offsets(node, offset):
	""" Calculate an intermediate position for VIA links
		:param offset: Offset factor to increase the distance of the positions"""

	logging.debug('Getting node offsets for ' + str(node))

	return offset % 2 == 1 and (node[0] - 20 * offset, node[1] + 20 * offset) or \
			(node[0] + 20 * offset, node[1] - 20 * offset)

