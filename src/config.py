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

# A tuple collection of the mobile nodes where traffic data should be collected from
# Example: '192.168.0.1', '127.0.0.1'
Nodes = ('10.0.0.1','10.0.0.5','10.0.0.7')

# A list of the interfaces to be monitored (separate by comma if more than one)
# Example: 'eth0', 'eth1
Interfaces = ('ath0','ath1')

# Which version of SNMP should be used (1 or 2c)
SnmpVersion = '2c'

# Read-only community string
Community = 'public'

# Interval for collecting traffic data in seconds
TrafficInterval = 2

#-----------------
# Network Topology
#-----------------

# Weathermap output file
TopologyImg = 'weathermap.png'

# Weathermap configuration file
TopologyConf = 'weathermap.conf'

# Whether traffic data is shown
ShowBandwidth = True

# Network backbone bandwidth (kilobits)
Bandwidth = 1024

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

# Simulate network traffic for when it's impossible to run on a live system
# For trafficmon, records random flunctuating traffic in RRDtool
# Should be used for development purposes only!
Simulate = False