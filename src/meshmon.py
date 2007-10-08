#!/usr/bin/env python2.5

__doc__ = """
MeshMon - Wireless Mesh Monitoring
Version 0.1 - Jerry Chong <zanglang@gmail.com>
"""

import sys
from linkmon import LinkMon
from trafficmon import TrafficMon
import meshweb, threads, util

if __name__ == "__main__":
	# create Javascript configuration 
	util.convert_to_js()
	
	# run monitors
	try:
		TrafficMon().main()
		LinkMon().main()
		meshweb.main()
		
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
	sys.exit()