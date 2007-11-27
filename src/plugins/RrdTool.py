__doc__ = """
MeshMon RRDtool/SNMP plugin
version 0.1 - Jerry Chong <zanglang@gmail.com>
"""

PLUGIN_INFO = {
			'NAME': 'RRDtool/SNMP/AODV',
			'AUTHOR': 'Jerry Chong',
			'VERSION': '0.1',
			'DESCRIPTION': 'RRDTool/SNMP/AODV gatherer and renderer backend plugin'
}

def initialize():
	import gatherers.rrdsink, logging, threads
	# finish initialization, start monitoring threads for router nodes
	logging.debug('Starting AODV thread')
	threads.add(gatherers.rrdsink.AodvThread())

	import nodes
	for node in nodes.collection:
		if (node.type == nodes.ROUTER):
			logging.debug('Starting SNMP poll thread for ' + `node.address`)
			threads.add(gatherers.rrdsink.GathererThread(node))

			import rendering.rrd
			logging.debug('Starting graphing thread for ' + `node.address`)
			threads.add(rendering.rrd.GraphingThread(node))

	import rendering.weathermap
	logging.debug('Starting weathermap thread')
	threads.add(rendering.weathermap.WeathermapThread())