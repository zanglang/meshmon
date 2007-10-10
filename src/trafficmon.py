__doc__ = """
Traffic Monitor for MeshMon
Version 0.1 - Jerry Chong <zanglang@gmail.com>

Based on meshtraffic.pl by Dirk Lessner, National ICT Australia
"""

import logging, sys
import aodv, config, nodes, snmp, threads

if (config.Debug):
	logging.basicConfig(level=logging.DEBUG)

def main():
	""" Initialize monitoring """
	print 'TrafficMon started.\nPress <Ctrl>-C to shut down.'
	# initialize interface indices for monitored nodes
	for node in config.Nodes:
		logging.debug('Initializing node ' + `node`)
		if nodes.find(node):
			continue
		n = nodes.create(node)
		n.type = nodes.ROUTER
		nodes.add(n)
		init_snmp(n)
	
	# finish initialization, start monitoring threads
	for node in nodes.collection:
		if (node.type == nodes.ROUTER):
			if (config.Simulate):
				logging.debug('Starting SNMP poll thread for ' + `node.address`)
				threads.add(backend.SnmpPollThread(node))	
			else:
				logging.debug('Starting simulated SNMP thread for ' + `node.address`)
				threads.add(backend.SimulationPollThread(node))
				
			logging.debug('Starting graphing thread for ' + `node.address`)
			threads.add(backend.GraphingThread(node))
	
def shutdown():
	""" Cleaning up """
	print 'Please wait while TrafficMon shuts down...'
	threads.terminate_all(wait=True)
	logging.shutdown()
	sys.exit()

def init_aodv(target):
	# TODO: GET AODV log here!
	############	
	text = None
	############
	
	aodv_entries = aodv.parse(text)
	for entry in aodv_entries:
		# check if it already exists
		dest = nodes.find(entry['destination'])
		if dest == None:
			# add newly discovered nodes to collection
			dest = nodes.create(entry['destination'])
			nodes.add(dest)
		elif dest.type != nodes.ROUTER
			# if node exists, but was not identified
			##### TODO: Probe check nodes for SNMP
			dest.type = nodes.GENERIC
				
		# also check for AODV gateway nodes
		gateway = nodes.find(entry['gateway'])
		if gateway == None:
			gateway = nodes.create(entry['gateway'])
			gateway.type = nodes.ROUTER
			nodes.add(gateway)
		else:
			if gateway.type != nodes.ROUTER:
				gateway.type = nodes.ROUTER		
		
		# add interfaces to node
		if entry['interface'] not in target.interfaces:
			target.interfaces += entry['interface']

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