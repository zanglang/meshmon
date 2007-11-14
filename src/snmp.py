
__doc__ = """
SNMP utility functions
Version 0.1 - Jerry Chong <zanglang@gmail.com>
"""

import config, thread
try:
	from pysnmp.entity.rfc3413.oneliner import cmdgen, ntforg
	from pysnmp.smi import builder
except:
	import sys
	print 'Python library PySNMP 4.x is required!'
	sys.exit()


# load the commonly used MIB definitions and other SNMP stuff
mib = builder.MibBuilder().loadModules('SNMPv2-MIB', 'IF-MIB', 'RFC1213-MIB')
cmd = cmdgen.CommandGenerator()
community = cmdgen.CommunityData('my-agent', config.Community, 0)

# maintain a global lock for multithreaded access
lock = thread.allocate_lock()

def get_address(target):
	""" Lookup an absolute contactable address for SNMP to use """
	return config.NodeAliases.has_key(target) \
			and config.NodeAliases[target] \
			or target


def load_symbol(module, object):
	""" Returns a set of OIDs given an MIB name """
	return mib.importSymbols(module, object)[0].getName()


def walk(target, objects):
	""" SNMP WALK query """
	
	lock.acquire()
	errorIndication, errorStatus, errorIndex, varBinds = cmd.nextCmd(
		community,
		cmdgen.UdpTransportTarget((get_address(target), 161)),
		objects
	)
	lock.release()
	
	if (errorIndication != None):
		raise Exception, 'SNMP error on %s: %s' % (target, errorIndication)
	# print errorStatus
	# print errorIndex
	return varBinds;


def get(target, objects):
	""" SNMP GET query """
	
	lock.acquire()
	errorIndication, errorStatus, errorIndex, varBinds = cmd.getCmd(
		community,
		cmdgen.UdpTransportTarget((get_address(target), 161)),
		objects
	)
	lock.release()
	
	if (errorIndication != None):
		raise Exception, 'SNMP error on %s: %s' % (target, errorIndication)
	# print errorStatus
	# print errorIndex
	return varBinds;


def bulk_get(target, objects, nonRepeaters = 0, maxRepetitions = 10):
	""" SNMP GET query """
	
	lock.acquire()
	errorIndication, errorStatus, errorIndex, varBinds = cmd.bulkCmd(
		community,
		cmdgen.UdpTransportTarget((get_address(target), 161)),
		nonRepeaters,
		maxRepetitions,
		*objects
	)
	lock.release()
	
	if (errorIndication != None):
		raise Exception, errorIndication
	# print errorStatus
	# print errorIndex
	return varBinds;


def notify(target, oid, value, confirm = False):
	""" SNMP trap message """

	# check notification type - inform or trap
	notify_type = confirm is True and 'inform' or 'trap'

	lock.acquire()
	errorIndication = ntforg.NotificationOriginator().sendNotification(
		community,
		cmdgen.UdpTransportTarget((get_address(target), 162)),
		notify_type,
		# TODO: we need a private mib
		('SNMPv2-MIB', 'coldStart'),
		(oid, value)
	)
	lock.release()
	
	if (errorIndication != None):
		raise Exception, errorIndication
