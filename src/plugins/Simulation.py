__doc__ = """
MeshMon RRDtool/SNMP plugin
version 0.1 - Jerry Chong <zanglang@gmail.com> 
"""

import config, logging, nodes, threads
import gatherers.simulatesink
import rendering.rrd
import rendering.weathermap

PLUGIN_INFO = {
			'NAME': 'Simulated RRDTool',
			'AUTHOR': 'Jerry Chong',
			'VERSION': '0.1',
			'DESCRIPTION': 'Simulated RRDTool/SNMP/AODV gatherer and renderer backend plugin'
}

def initialize():
	# generate and update nodes collection
	gatherers.simulatesink.populate()
	logging.debug('Starting simulator thread')
	threads.add(gatherers.simulatesink.SimulatorThread())
	
	for node in nodes.collection:
		if (node.type == nodes.ROUTER):
			logging.debug('Starting graphing thread for ' + `node.address`)		
			threads.add(rendering.rrd.GraphingThread(node))
							
	logging.debug('Starting weathermap thread')
	threads.add(rendering.weathermap.WeathermapThread())
