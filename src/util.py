
__doc__ = """
MeshMon utility functions
Version 0.1 - Jerry Chong <zanglang@gmail.com>
"""

import config

def convert_to_js():
	"""Outputs current Meshmon configuration into Javascript"""
	
	# array for images we will be generating
	files = [config.ImgPath + '/' + node + '-' + interface + '.' +
											config.ImgFormat.lower()
			for node in config.Nodes
			for interface in config.Interfaces]
	
	# dump into file
	f = open('config.js', 'w')
	f.write("files = ['" + "','".join(files) + "']\n")
	f.write("interval = " + str(config.TrafficInterval * 1000) + "\n")
	f.close()