__doc__ = """
MeshMon RRDtool/SNMP plugin
version 0.1 - Jerry Chong <zanglang@gmail.com> 
"""

import config, logging, nodes, threads
import gatherers.rrdsink
import rendering.rrd
import rendering.weathermap

PLUGIN_INFO = {
			'NAME': 'RRDtool/SNMP/AODV',
			'AUTHOR': 'Jerry Chong',
			'VERSION': '0.1',
			'DESCRIPTION': 'RRDTool/SNMP/AODV gatherer and renderer backend plugin'
}

def initialize():
	# finish initialization, start monitoring threads for router nodes
	logging.debug('Starting AODV thread')
	threads.add(gatherers.rrdsink.AodvThread())
	
	for node in nodes.collection:
		if (node.type == nodes.ROUTER):			
			if not config.Simulate:
				logging.debug('Starting SNMP poll thread for ' + `node.address`)
				threads.add(gatherers.rrdsink.GathererThread(node))	
			else:
				logging.debug('Starting simulated SNMP thread for ' + `node.address`)
				threads.add(gatherers.rrdsink.SimulationGathererThread(node))
				
			logging.debug('Starting graphing thread for ' + `node.address`)
			threads.add(rendering.rrd.GraphingThread(node))
				
	logging.debug('Starting weathermap thread')
	threads.add(rendering.weathermap.WeathermapThread())