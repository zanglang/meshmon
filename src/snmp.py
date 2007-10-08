
__doc__ = """
SNMP utility functions
Version 0.1 - Jerry Chong <zanglang@gmail.com>
"""

import config
try:
	from pysnmp.entity.rfc3413.oneliner import cmdgen, ntforg
	from pysnmp.smi import builder
except:
	print 'Python library PySNMP 4.x is required!'
	sys.exit()

# load the commonly used MIB definitions
mib = builder.MibBuilder().loadModules('SNMPv2-MIB', 'IF-MIB', 'RFC1213-MIB')

def load_symbol(module, object):
	""" Returns a set of OIDs given an MIB name """
	return mib.importSymbols(module, object)[0].getName()
	
def walk(target, objects):
	""" SNMP WALK query """
	errorIndication, errorStatus, errorIndex, varBinds = \
			cmdgen.CommandGenerator().nextCmd(
		cmdgen.CommunityData('my-agent', config.Community, 0),
		cmdgen.UdpTransportTarget((target, 161)),
		objects
	)
	if (errorIndication != None):
		raise Exception, errorIndication
	# print errorStatus
	# print errorIndex
	return varBinds;
	
def get(target, objects):
	""" SNMP GET query """
	errorIndication, errorStatus, errorIndex, varBinds = \
			cmdgen.CommandGenerator().getCmd(
		cmdgen.CommunityData('my-agent', config.Community, 0),
		cmdgen.UdpTransportTarget((target, 161)),
		objects
	)
	if (errorIndication != None):
		raise Exception, errorIndication
	# print errorStatus
	# print errorIndex
	return varBinds;

def bulk_get(target, objects, nonRepeaters = 0, maxRepetitions = 10):
	""" SNMP GET query """
	errorIndication, errorStatus, errorIndex, varBinds = \
			cmdgen.CommandGenerator().bulkCmd(
		cmdgen.CommunityData('my-agent', config.Community, 0),
		cmdgen.UdpTransportTarget((target, 161)),
		nonRepeaters,
		maxRepetitions,
		*objects
	)
	if (errorIndication != None):
		raise Exception, errorIndication
	# print errorStatus
	# print errorIndex
	return varBinds;

def notify(target, oid, value, confirm = False):
	""" SNMP trap message """
	
	# check notification type - inform or trap
	notify_type = confirm is True and 'inform' or 'trap'
	
	errorIndication = ntforg.NotificationOriginator().sendNotification(
		cmdgen.CommunityData('my-agent', config.Community, 0),
		cmdgen.UdpTransportTarget((target, 162)),
		notify_type,
		# TODO: we need a private mib
		('SNMPv2-MIB', 'coldStart'),
		(oid, value)
	)
	if (errorIndication != None):
		raise Exception, errorIndication
	