#!/usr/bin/env python2.5

__doc__ = """
MeshMon - Wireless Mesh Monitoring
Version 0.1 - Jerry Chong <zanglang@gmail.com>
"""

import logging, sys
import config, nodes, threads, webserver

if (config.Debug):
	logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
	""" Initialize monitoring """
	print 'TrafficMon started.\nPress <Ctrl>-C to shut down.'
	
	backend = None
	try:
		# Initialize backends. This is currently hardcoded as we only
		# have one method to gather and render data at the moment
		MODULE = 'RrdTool'
		backend = __import__('plugins.' + MODULE)
		plugin = backend.__dict__[MODULE]
		if not plugin.__dict__.has_key('initialize') or \
				not plugin.__dict__.has_key('PLUGIN_INFO'):
			raise Exception, 'module not a valid plugin.'
	except:
		import traceback
		logging.error('Error loading plugin:')
		traceback.print_exc()
		sys.exit()
	print 'Loaded plugin', plugin.PLUGIN_INFO['NAME']
	
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
		
		plugin.initialize()
		webserver.start()
		
		num_threads = threads.size()
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