__doc__ = """
AODV parser module
Version 0.1 - Jerry Chong <zanglang@gmail.com>
"""

import re, sys

def parse_proc_file(filename):
	# read /proc file contents
	try:
		f = open(filename)
	except IOError:
		print 'Could not open ' + filename + ', aborting!'
		return
	# skip the first line/file descriptive header
	proc = f.readline()
	
	# compile regex
	# Example: 10.0.1.1	10.0.1.1	ath0	a	50	1024	2	V
	p = re.compile('^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+' +	# destination
			'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+' +		# gateway
			'(\w{3,4}\d)\s+' +	# interface
			'(\w)\s+' +			# 802.11 type
			'(\d{1,2})\s+'		# channel
			'(\d+)\s+' +		# bytes/sec
			'(\d+)\s+' +		# packets/sec
			'(\w+)?\s*')			# flag
	
	entries = []
	for line in f:
		# print out matches for debugging purposes
		entry = p.match(line).groups()
		entries += {
			'destination': entry[0],
			'gateway': entry[1],
			'interface': entry[2],
			'80211type': entry[3],
			'channel': entry[4],
			'bytes': entry[5],
			'packets': entry[6],
			'flag': entry[6]
		}
		
	print entries[0]['destination']

if __name__ == "__main__":
	# first argument as file to read
	filename = len(sys.argv) > 1 and sys.argv[1] \
			or 'example-proc-file.txt' # default test file
	parse_proc_file(filename)