__doc__ = """
Traffic Monitor for MeshMon
Version 0.1 - Jerry Chong <zanglang@gmail.com>

Based on meshtraffic.pl by Dirk Lessner, National ICT Australia
"""

import logging, sys
import config, nodes, gatherers.rrdtool, threads

if (config.Debug):
	logging.basicConfig(level=logging.DEBUG)

def main():
	""" Initialize monitoring """
	print 'TrafficMon started.\nPress <Ctrl>-C to shut down.'
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
			
	### BUG: We need to refresh AODV multiple times!
	
def shutdown():
	""" Cleaning up """
	print 'Please wait while TrafficMon shuts down...'
	threads.terminate_all(wait=True)
	logging.shutdown()
	sys.exit()

#-----------------------------------------------------------------

if __name__ == "__main__":
	mon = TrafficMon()
	mon.main()
	# If we have worker threads running...
	num_threads = threads.len()
	if num_threads > 0:
		print str(num_threads), 'threads executing...'
		while 1:
			try:
				input = raw_input()
			except (EOFError, KeyboardInterrupt):
				break
	else:
		# no threads running at all! (possibly bad configuration)
		print 'Nothing to monitor.'
	mon.destroy()