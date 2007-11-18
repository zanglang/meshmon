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
vmargin = 200
# number of pixels in left/right margin
hmargin = 200
# temporary table for allocated nodes
allocations = {0: []}
# free layers available
layers = [0]
# highest layer available
highlayer = 0
def assign(node, position):
	""" Assign a fixed position to node """

	logging.debug('Assigning node %s to %s' % (node.address, position))
	node.position = position
	node.position_fixed = True

	# keep positions in memory for future
	positions[node.address] = position

	global width, height
	# adjust horizontal
	if position[0] > width + hmargin:
		width = position[0] + hmargin
		print 'Adjusting topology width to', width, 'for', position
	if position[1] > height + vmargin:
	 	height = position[1] + vmargin
	 	print 'Adjusting topology height to', height, 'for', position


def add(node):
	""" Add a mesh node into the topology and regenerate positions """

	# node is already defined?
	if node in collection:
		return
	collection.append(node)

	logging.debug('Adding new node %s to topology' % node.address)

	# determine positions for node
	if positions.has_key(node.address):
		# if node already has static allocations available

		node.position = positions[node.address]
		node.position_fixed = True
		layer = (positions[node.address][1] / buffer)
		logging.debug('Assigned node to %s (layer %d)' %
				(positions[node.address], layer))

	elif config.DynamicTopology:
		# pick a layer and insert the node
		layer = random.choice(layers)
		node.position_fixed = False

	global highlayer

	# place node in layer allocation
	if not allocations.has_key(layer):

		newlayers = [num + 1 for num in xrange(highlayer, layer)]
		layers.extend(newlayers)

		highlayer = layer
		logging.debug('Adding new layers to %d' % highlayer)

		for l in newlayers:
			allocations[l] = []

	logging.debug('Adding node to layer %d' % layer)
	allocations[layer].append(node)

	# if a layer already has 3 nodes we consider it "full".
	# Expand to a new layer to be used later
	#if (len(allocations[layer]) >= 4):
	#	layers.remove(layer)

	for layer, allocation in allocations.items():

		# does this layer need adjusting?
		pnode = [n for n in allocation if not n.position_fixed]
		if len(pnode) == 0:
			continue

		parts = partition([n for n in allocation if n.position_fixed], buffer)
		allocated = 0
		
		for n in pnode:
			if len(parts) > 0:
				part = parts.pop(0)
				n.position = (part.stop + 1, layer * buffer + vmargin/2)
			elif allocated > 0:
				n.position = (allocation[len(allocation) - 2].position[0] + buffer,
						layer * buffer + vmargin/2)
			else:
				n.position = (hmargin/2, layer * buffer + vmargin/2)
			allocated += 1 

		logging.debug('Adjusting node %s to %s' %
				(n.address, str(n.position)))

	allocations[layer].sort(lambda nodex, nodey:
			nodex.position[0] < nodey.position[0] and -1 or 1)

	# Readjust the topology. Increase width and height to expected value
	global width, height

	xheight = (highlayer - 1) * buffer + vmargin * 2
	if height < xheight:
		height = xheight
		print 'Height adjusted to %d' % height

	xwidth = max((len(allocations[layer]) - 1) * buffer + hmargin * 2,
			n.position[1] + hmargin)
	if width < xwidth:
		width = xwidth
		print 'Width adjusted to %d' % width

	# number of pixels between nodes in the same horizantal line
		#gap = int(math.ceil(width/(len(allocation)+1)))
		#offset = gap

		# set positions of nodes on layer
		#for n in allocation:
		#	if n.position_fixed:
		#		continue
		#	n.position = (offset, layer * buffer + vmargin/2)
		#	offset += gap
		#	logging.debug('Adjusting node %s to %s' %
		#			(n.address, str(n.position)))



def initialize():
	""" Initializing topology. Read preconfigured node positions """

	# positions were defined in config file
	for address, position in config.NodePositions.items():
		positions[address] = position


def partition(allocation, gap):
	""" Simple line partitioning function. Doesn't handle anything complicated,
		so be careful when using it! """

	slices = []

	for node in allocation:
		lbound = node.position[0] - gap
		if lbound < 0:
			lbound = 0
		hbound = node.position[0] + gap

		merged = False
		for s in slices:
			if s.stop in xrange(lbound, hbound):
				slices.remove(s)
				slices.append(slice(s.start, hbound))
				merged = True
				break
			elif s.start in xrange(lbound, hbound):
				slices.remove(s)
				slices.append(slice(lbound, s.stop))
				merged = True
				break

		if not merged:
			slices.append(slice(lbound, hbound))

	return slices