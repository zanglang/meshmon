__doc__ = """
MeshMon data-gathering backend classes
Version 0.1 - Jerry Chong <zanglang@gmail.com>

Based on meshtraffic.pl by Dirk Lessner, National ICT Australia
"""

import os, random, rrdtool
import config, logging, nodes, threads, topology

random.seed()

# predefined positions and addresses of nodes
NODES = {
	'192.168.1.1': {
		'neighbours': {
			'ath3': '192.168.1.2',
			'ath4': '192.168.1.4',
			'ath5': '192.168.1.5'
		},
		'positions': (100, 100)
	},
	'192.168.1.2': {
		'neighbours': {
			'ath3': '192.168.1.1',
			'ath4': '192.168.1.5',
			'ath5': '192.168.1.3'
		},
		'positions': (300, 100)
	},
	'192.168.1.4': {
		'neighbours': {
			'ath4': '192.168.1.1',
			'ath5': '192.168.1.8',
			'ath6': '192.168.1.7'
		},
		'positions': (100, 300)
	},
	'192.168.1.5': {
		'neighbours': {
			'ath3': '192.168.1.2',
			'ath4': '192.168.1.7',
			'ath5': '192.168.1.6'
		},
		'positions': (300, 300)
	},
	'192.168.1.7': {
		'neighbours': {
			'ath4': '192.168.1.4',
			'ath5': '192.168.1.5',
			'ath6': '192.168.1.8'
		},
		'positions': (100, 500)
	},
	'192.168.1.8': {
		'neighbours': {
			'ath2': '192.168.1.7',
			'ath1': '192.168.1.4',
			'ath3': '192.168.1.9'
		},
		'positions': (300, 500)
	}
}

_X = {
	
	'192.168.1.6': {
		'neighbours': {
			'ath5': '192.168.1.2',
			'ath6': '192.168.1.3'
		},
		'positions': (500, 300)
	},
	'192.168.1.9': {
		'neighbours': {
			'ath2': '192.168.1.6',
			'ath4': '192.168.1.8'
		},
		'positions': (500, 500)
	}
}

def populate():
	for address, details in NODES.items():
		# add node to nodes list
		node = nodes.find(address)
		if node == None:
			node = nodes.create(address)
			nodes.add(node)
		node.type = nodes.ROUTER
		
		# temporary neighbours store
		node._neighbours = []
		# actual store for current neighbours
		node.neighbours = {}
		# number of rrdtool databases used
		node.rrd_files = []
		# keep track of incoming/outgoing traffic
		node.in_octets = {}
		node.out_octets = {}
		
		# assign node positions
		topology.assign(node.address, details['positions'])
		node.position = details['positions']
		
		# initialize interfaces and neighbouring links
		for interface, neighbour in details['neighbours'].items():
			if neighbour not in NODES.keys():
				continue
			nnode = nodes.find(neighbour)
			if nnode == None:
				nnode = nodes.create(neighbour)
				nodes.add(nnode)
			
			# update node's neighbours and initial connections
			node.neighbours[nnode] = interface
			node._neighbours.append(nnode)
			
			if interface not in node.interfaces:
				node.interfaces.append(interface)
				
				# check path to rrdtool database
				rrd_file = config.RrdTemplate.substitute({
					'dir': config.RrdPath,
					'host': node.address,
					'if': interface
				})
				
				if rrd_file in node.rrd_files:
					continue
				
				if not os.path.exists(rrd_file):
					print 'Creating RRDtool database at ' + `rrd_file`
					try:
						rrdtool.create(rrd_file,
							#'-b now -60s',				# Start time now -1 min
							'-s ' + `config.TrafficInterval`,	# interval
							'DS:traffic_in:COUNTER:' + `config.TrafficInterval * 2` + ':0:3500000',
							'DS:traffic_out:COUNTER:' + `config.TrafficInterval * 2` + ':0:3500000',
							'RRA:LAST:0.1:1:720',		# 720 samples of 1 minute (12 hours)
							#'RRA:LAST:0.1:5:576',		# 576 samples of 5 minutes (48 hours)
							'RRA:AVERAGE:0.1:1:720',	# 720 samples of 1 minute (12 hours)
							#'RRA:AVERAGE:0.1:5:576',	# 576 samples of 5 minutes (48 hours)
							'RRA:MAX:0.1:1:720'			# 720 samples of 1 minute (12 hours)
							#'RRA:MAX:0.1:5:576'		# 576 samples of 5 minutes (48 hours)
						)
					except rrdtool.error, e:
						# this should be quite serious. Handle immediately!
						logging.error(e)
						raise Exception, 'Unable to create RRDtool database!'
				else:
					print node.address, 'using RRDtool database at ', rrd_file
				node.rrd_files.append(rrd_file)		

				
class SimulatorThread(threads.MonitorThread):
	""" Thread for generating simulated data """

	def __init__(self):
		super(SimulatorThread, self).__init__()
		self.func = self.loop_simulate
		self.interval = config.TrafficInterval
		
	def loop_simulate(self):
		for node in nodes.collection:
			node.neighbours.clear()
	
		for node in nodes.collection:
			logging.debug('loop_simulate for ' + `node.address`)
			
			# pick random neighbours matched with interfaces
			nnodes = []
			chose = 0
			for num in xrange(random.randint(0, len(node.interfaces))):
				random_node = random.choice(node._neighbours)
				nnodes.append(random_node)
			
			ninterfaces = random.sample(node.interfaces,
					len(nnodes))
			# clear the neighbours dictionary
			node.neighbours.clear()
			# update the table
			for index, n in enumerate(nnodes):
				if len(node.neighbours) == 3 or len(n.neighbours) == 3:
					continue
				node.neighbours[n] = ninterfaces[index]
				
			# 128 kbytes upstream/64 downstream
			for index, rrd_file in enumerate(node.rrd_files):
				
				if not node.in_octets.has_key(rrd_file):
					node.in_octets[rrd_file] = 0
				if not node.out_octets.has_key(rrd_file):
					node.out_octets[rrd_file] = 0
					
				in_octets = random.randint(0, 128000)
				out_octets = random.randint(0, 64000)
				
				adjust = random.randint(0, 100)
				if adjust < 25:
					in_octets /= 1000
				elif adjust < 80:
					in_octets /= 2
					
				adjust = random.randint(0, 100)
				if adjust < 25:
					out_octets /= 1000
				elif adjust < 80:
					out_octets /= 2
					
				node.in_octets[rrd_file] += in_octets
				node.out_octets[rrd_file] += out_octets
			
				logging.debug('Updating RRDtool in:' + str(node.in_octets[rrd_file]) +
					' out:' + str(node.out_octets[rrd_file]))
			
				# push the generated numbers into rrdtool
				try:
					rrdtool.update(rrd_file,
						'-t',
						'traffic_in:traffic_out',
						'N:' + str(node.in_octets[rrd_file]) +
							':' + str(node.out_octets[rrd_file])
					)
				except rrdtool.error, e:
					logging.error(e)
				