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

# node positions temporary store
node_positions = {}

#####
# TODO Chunks
# 1. Link thread by SNMP (can use AODV instead)

def add(node):
    """ Add a mesh node into the topology and regenerate positions """
    collection.append(node)
    try:
        node_positions[node] = positions.pop()
        logging.debug('Node ' + node + ' assigned to ' + str(node_positions[node]))
    except IndexError:
        logging.error('FIXME: Ran out of node positions.')
        node_positions[node] = (0,0)

#-------------------------------------------------------------------------------
def get_intermediate(node1, node2):
    """ Calculate an intermediate position for VIA links """
    logging.debug('Getting intermediate node for ' + str(node1) + ' ' + str(node2))
    x = (node1[0] + node2[0])/2
    y = (node1[1] + node2[1])/2
    if abs(node1[0] - node2[0]) <  abs(node1[1] - node2[1]):
        return (x - 40, y), (x + 40, y)
    else:
        return (x, y - 40), (x, y + 40)

def parse_routes(routes):
    """ Parse PySNMP routes into simple lists """    
    from pysnmp.proto.rfc1155 import ipAddressPrettyOut
    return map(lambda r: ipAddressPrettyOut(r[0][1]), routes)