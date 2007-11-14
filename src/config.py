__doc__ = """
MeshMon Configuration
Version 0.1 - Jerry Chong <zanglang@gmail.com>

This file is imported as a Python module during runtime.
To change MeshMon's options change the corresponding value,
but make sure that the syntax is valid Python.
"""

from string import Template

#--------
# Logging
#--------

# Debug output (= True) or no debug output (= False)
Debug = True

#------------
# Monitoring
#------------

# Main plugin to use. Plugins determine the setup of gatherers and renderers
# to deploy. Default: 'RrdTool' or 'Simulation'
MainPlugin = 'RrdTool'

# A tuple collection of the mobile nodes where traffic data should be collected from
# Example: '192.168.0.1', '127.0.0.1'
Nodes = ('192.168.0.50',)
#Nodes = []

# A list of the interfaces to be monitored (separate by comma if more than one)
# Example: 'eth0', 'eth1
# NOTE: No longer used
# Interfaces = ('ath0','ath1')

# Which version of SNMP should be used (1 or 2c)
SnmpVersion = '2c'

# Read-only community string
Community = 'public'

# Interval for collecting traffic data in seconds
TrafficInterval = 5

#-----------------
# Network Topology
#-----------------

# Dynamically calculate topology
DynamicTopology = True

# Additional configuration for topology.
# 	Using the 'config' setting lets topology.py to initialize nodes'
#	positions from a Python dict first.
# Default: Read from config.NodePositions. Leave path as None, or replace it
#	with a dictionary structure
# Format: ('<plugin/definitions type>', '<file path>')
# Example: ('static', 'coords.txt')
TopologySettings = ('config', None)

# Weathermap output file
TopologyImg = 'weathermap.png'

# Weathermap configuration file
TopologyConf = 'weathermap.conf'

# Whether traffic data is shown
# Available options: percent, bits, interface, none
ShowBandwidthLabel = 'interface'

# Network backbone bandwidth (kilobits)
Bandwidth = 100

#---------
# RRDtool
#---------

# Directory to locate RRDtool databases
RrdPath = '.'

# Defines filename location template for rrdtool databases
#
# Available options:
# - $dir: directory
# - $host: host name or IP address
# - $if: interface name
#
# Examples
# - $dir/$host/$if.rrd: Separate database by host folders
RrdTemplate = Template('$dir/$host-$if.rrd')

# Interval to refresh rrdtool output image (in seconds)
RefreshInterval = 5

# Time interval to display on graph (hour|day|week|month|year)
GraphInterval = 'hour'

# Directory to output RRDtool graphs
ImgPath = '.'

# Output image format
ImgFormat = 'PNG'

# Defines filename location template for rrdtool output images
# Similar to RrdTemplate
#
# Additional options (other than RrdTemplate):
# - $imgdir: directory for images (different from $dir)
# - $ext: File extension
# - $int: Graph interval
ImgTemplate = Template('$imgdir/$host-$if.$ext')

#---------
# Testing
#---------

# Graceful shutdown waits for all threads to stop before quitting the program
# Recommended, obviously, but may be turned off for development
GracefulShutdown = False

#-----------
# Web Server
#-----------

# Change the port of the internal web server (default: 8080)
WebServerPort = 8081

#---------------
# Extra Settings
#---------------

# preset node positions in pixels
# Example: {'192.168.0.1': (100,100)}
NodePositions = {
	'192.168.0.50': (100, 100),
	'192.168.0.51': (100, 300)
}

# Temporary table of aliases when monitoring over external interface
NodeAliases = {
	'192.168.0.50': '192.168.1.50'
}