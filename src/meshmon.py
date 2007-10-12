#!/usr/bin/env python2.5

__doc__ = """
MeshMon - Wireless Mesh Monitoring
Version 0.1 - Jerry Chong <zanglang@gmail.com>
"""

import logging, sys
import config, gatherers.rrdtool, nodes, threads, util

if (config.Debug):
	logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
	""" Initialize monitoring """
	print 'TrafficMon started.\nPress <Ctrl>-C to shut down.'
	
	# create Javascript configuration 
	util.convert_to_js()
	### TODO: move into web.py
	
	# run monitors
	try:
		# initialize interface indices for monitored nodes
		# These are router nodes which we have explicitly pointed out to be polled
		for node in config.Nodes:
			logging.debug('Initializing node ' + `node`)
			if nodes.find(node):
				continue
			n = nodes.create(node)
			n.type = nodes.ROUTER
			nodes.add(n)
		
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
				
		##### TODO: start web.py
		
		num_threads = threads.len()
		if num_threads > 0:
			print str(num_threads), 'threads executing...'
			while 1:
				try:
					input = raw_input()
				except (EOFError, KeyboardInterrupt):
					break
		else:
			print 'Nothing to monitor.'
	except (EOFError, KeyboardInterrupt):
		pass
	
	print 'Please wait while MeshMon shuts down...'
	threads.terminate_all(wait=True)
	logging.shutdown()
	sys.exit()