__doc__ = """
MeshMon topology generation
Version 0.1 - Jerry Chong <zanglang@gmail.com>

Based on meshtraffic.pl by Dirk Lessner, National ICT Australia
"""

# global routing table store
routes = {}
collection = []

# BUG: These are preselected locations. Only 4 nodes, anymore can't be shown..
# positions = deque(['75 360', '250 200', '425 360', '250 520'])
# TODO: read this and 'via' paths from a file so we can get a perfect graph
positions = deque([(400,260), (100,260), (250,260)])
#positions = deque([(350,460),(150,460), (250,60), (250,260)])

# size of current mesh topology
width = 0
height = 0

#####
# TODO Chunks
# 1. Link thread by SNMP (can use AODV instead)

def add(node):
	""" Add a mesh node into the topology and regenerate positions """
	collection.append(node)
	try:
		node.position = positions.pop()
		logging.debug('Node ' + node + ' assigned to ' + str(node.position))
	except IndexError:
		logging.error('FIXME: Ran out of node positions.')
		node.position = (0,0)

#-------------------------------------------------------------------------------
def parse_routes(routes):
	""" Parse PySNMP routes into simple lists """	
	from pysnmp.proto.rfc1155 import ipAddressPrettyOut
	return map(lambda r: ipAddressPrettyOut(r[0][1]), routes)