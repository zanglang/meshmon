__doc__ = """
MeshMon topology generation
Version 0.1 - Jerry Chong <zanglang@gmail.com>

Based on meshtraffic.pl by Dirk Lessner, National ICT Australia
"""

import logging, math, random
import config

# temporary table for all nodes added
collection = []
# tables for pre-read node positions
positions = {}

# size of current mesh topology
width = 0
height = 0
# number of pixels between nodes
buffer = 200
# number of pixels in top/bottom margin
vmargin = 120
# number of pixels in left/right margin
hmargin = 250
# temporary table for allocated nodes
allocations = {}
# free layers available
layers = [0,1]
# highest layer available
highlayer = 1
def assign(address, position):
	positions[address] = position
	
	global width, height
	# adjust horizantal
	print position[0]
	if position[0] > width + hmargin:
		width = position[0] + hmargin
		print 'Adjusting width to', width, 'for', position
	if position[1] > height + vmargin:
	 	height = position[1] + vmargin


def add(node):
	""" Add a mesh node into the topology and regenerate positions """
	
	if node in collection:
		return
	collection.append(node)
	
	logging.debug('Adding new node %s to topology' % node.address)
	
	# check if coordinates were previously defined
	### TODO: add plugin to read NSU/2 files
	if positions.has_key(node.address):
		
		logging.debug('Assigned node to ' + str(positions[node.address]))
		node.position = positions[node.address]
		
	elif config.DynamicTopology:
		global height, highlayer
		
		# pick a layer and insert the node
		layer = random.choice(layers)
		if not allocations.has_key(layer):
			allocations[layer] = []
			
		logging.debug('Adding node to layer %d' % layer)		
		allocations[layer].append(node)
		
		# if a layer already has 3 nodes we consider it "full".
		# Expand to a new layer to be used later
		if (len(allocations[layer]) == 3):
			layers.remove(layer)
			highlayer += 1
			layers.append(highlayer)
			logging.debug('Adding new layer %d' % highlayer)
			
		# Readjust the topology. Increase width and height if necessary
		# Note: using 120 pixels for top/bottom margins
		if height <= highlayer * buffer + vmargin:
			height += buffer			
			logging.debug('Height adjusted to %d' % height)
			
		for layer, allocation in allocations.items():
			# number of pixels between nodes in the same horizantal line
			gap = int(math.ceil(width/(len(allocation)+1)))
			offset = gap
			
			# set positions of nodes on layer
			for n in allocation:
				n.position = (offset, layer * buffer + vmargin/2)
				offset += gap
				logging.debug('Adjusting node %s to %s' %
						(node.address, str(node.position)))
						
	else:
		# any other methods? Just make sure everything gets adjusted properly!
		pass