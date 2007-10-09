# node engine

# enumerated types of nodes, used for
# 	differentiating the capabilities of nodes
MOBILE,		# mobile devices
ROUTER,		# mesh routers. assume to support SNMP
GENERIC,	# generic nodes
UNKNOWN = range(3)

# currently existing nodes
collection = []

class _Node:
	""" Represents a mesh node in the current topology """
	def __init__(self, address):
		self.address = address
		self.interfaces = []
		
def add(Node):
	""" Add nodes for collection """
	collection.append(Node)

def create(target):
	""" Create new mesh node instance """
	return Node(target)
	
def find(target):
	""" Find the node in collection with the given IP address """
	for n in collection:
		if n.address == target:
			return n
	return None
	