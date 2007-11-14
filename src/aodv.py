__doc__ = """
AODV parser module
Version 0.1 - Jerry Chong <zanglang@gmail.com>
"""

import re, sys

def parse(text):
	""" Parse a text block and returns a dictionary array of AODV information
	:param text: text block containing AODV metadata """

	# compile regex
	# Example: 10.0.1.1	10.0.1.1	ath0	a	50	1024	2	V
	pattern = re.compile('^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+' +	# destination
			'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+' +		# gateway
			'(\w{3,4}\d)\s+' +	# interface
			'(\w)\s+' +			# 802.11 type
			'(\d{1,2})\s+'		# channel
			'(\d+)\s+' +		# sent
			'(\d+)\s*' +		# received
			'(\w+)?')		# flag

	# digest text file into AODV links to neighbouring nodes
	entries = {}
	for line in text.split('\n'):

		line = line.strip()
		result = pattern.match(line)
		if result is None:
			continue

		entry = result.groups()
		# interface as key
		entries[entry[2]] = ({
			'destination': entry[0],
			'gateway': entry[1],
			#'interface': entry[2],
			#'80211type': entry[3],
			#'channel': entry[4],
			'sent': entry[5],
			'received': entry[6]
			#'flag': entry[7]
		})

	return entries


#------------------------------------------------------------------------------
def parse_proc_file(filename):
	""" Read /proc file contents for AODV information
	:param filename: Path to file containing AODV metadata """
	try:
		f = open(filename)
	except IOError:
		print 'Could not open ' + filename + ', aborting!'
		return None

	# skip the first line/file descriptive header
	f.readline()

	# read contents of file and pass to the parsing function
	text = f.read()
	entries = parse(text)
	f.close()
	return entries


#------------------------------------------------------------------------------
if __name__ == "__main__":
	# first argument as file to read
	filename = len(sys.argv) > 1 and sys.argv[1] \
			or 'example-proc-file.txt' # default test file
	print(parse_proc_file(filename))