__doc__ = """
MeshMon RRDtool/SNMP plugin
version 0.1 - Jerry Chong <zanglang@gmail.com> 
"""

import logging, nodes, threads
import gatherers.rrdtool
import rendering.rrdtool

PLUGIN_INFO = {
			'NAME': 'RRDtool/SNMP/AODV',
			'AUTHOR': 'Jerry Chong',
			'VERSION': '0.1',
			'DESCRIPTION': 'RRDTool/SNMP/AODV gatherer and renderer backend plugin'
}

def initialize():
	# finish initialization, start monitoring threads for router nodes
	logging.debug('Starting AODV thread for ' + `node.address`)
	threads.add(gatherers.rrdtool.AodvThread(node))
	
	# TODO: modularize backends
	for node in nodes.collection:
		if (node.type == nodes.ROUTER):
			if (config.Simulate):
				logging.debug('Starting SNMP poll thread for ' + `node.address`)
				threads.add(gatherers.rrdtool.SnmpPollThread(node))	
			else:
				logging.debug('Starting simulated SNMP thread for ' + `node.address`)
				threads.add(gatherers.rrdtool.SimulationPollThread(node))
				
			logging.debug('Starting graphing thread for ' + `node.address`)
			threads.add(rendering.rrdtool.GraphingThread(node))