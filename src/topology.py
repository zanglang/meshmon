__doc__ = """
MeshMon topology generation
Version 0.1 - Jerry Chong <zanglang@gmail.com>

Based on meshtraffic.pl by Dirk Lessner, National ICT Australia
"""

import math, random 

# temporary table for all nodes added
collection = []

# size of current mesh topology
width = 500.0
height = 520.0
# number of pixels between nodes
buffer = 200.0
# number of pixels in top/bottom margin
vmargin = 120.0
# temporary table for allocated nodes
allocations = {}
# free layers available
layers = [0,1]
# highest layer available
highlayer = 1

#####
# TODO Chunks
# 1. Link thread by SNMP (can use AODV instead)

def add(node):
	""" Add a mesh node into the topology and regenerate positions """
	collection.append(node)
	"""try:
		node.position = positions.pop()
		logging.debug('Node ' + node + ' assigned to ' + str(node.position))
	except IndexError:
		logging.error('FIXME: Ran out of node positions.')
		node.position = (0,0)"""
	
	if config.DynamicTopology:		
		# pick a layer and insert the node
		layer = random.choice(layers)
		if not allocations.has_key(layer):
			allocations[layer] = []
		allocations[layer].append(node)
		# if a layer already has 3 nodes we consider it "full".
		# Expand to a new layer to be used later
		if (len(allocations[layer]) == 3):
			layers.remove(layer)
			highlayer += 1
			layers.append(highlayer)
		# Readjust the topology. Increase width and height if necessary
		# Note: using 120 pixels for top/bottom margins
		if height <= highlayer * buffer + vmargin:
			height += buffer
		for layer, allocation in allocations.items():
			# number of pixels between nodes in the same horizantal line
			gap = int(math.ceil(width/(len(allocation)+1)))
			offset = gap
			# set positions of nodes on layer
			for n in allocation:
				n.position = (offset, layer * buffer + vmargin/2)
				offset += gap
	else:
		##### TODO: Check if coordinates were previously defined
		pass