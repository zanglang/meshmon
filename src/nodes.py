__doc__ = """
MeshMon node management
Version 0.1 - Jerry Chong <zanglang@gmail.com>

Based on meshtraffic.pl by Dirk Lessner, National ICT Australia
"""

import topology

# enumerated types of nodes, used for
# 	differentiating the capabilities of nodes
MOBILE,		# mobile devices
ROUTER,		# mesh routers. assume to support SNMP
GENERIC,	# generic nodes
UNKNOWN = range(4)	# this method of doing Python enumerating is not desirable

# currently existing nodes
collection = []

class _Node:
	""" Represents a mesh node in the current topology """
	def __init__(self, address):
		self.address = address
		self.interfaces = []
		self.neighbours = []
		self.type = UNKNOWN
		
def add(target):
	""" Add nodes for collection """
	collection.append(target)
	# renew mesh topology
	topology.add(target)
	topology.refresh()

def create(target):
	""" Create new mesh node instance """
	return Node(target)
	
def find(target):
	""" Find the node in collection with the given IP address """
	for n in collection:
		if n.address == target:
			return n
	return None
	