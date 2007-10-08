#!/usr/bin/env python2.5

__doc__ = """
MeshMon - Wireless Mesh Monitoring
Version 0.1 - Jerry Chong <zanglang@gmail.com>
"""

from sys import exit
from time import sleep
from linkmon import LinkMon
from trafficmon import TrafficMon
import util

if __name__ == "__main__":
	# create Javascript configuration 
	util.convert_to_js()
	
	thread_pool = util.ThreadPool()
	
	# run monitors
	try:
		TrafficMon().main()
		LinkMon().main()
		
		num_threads = thread_pool.len()
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
	thread_pool.terminate()
	exit()