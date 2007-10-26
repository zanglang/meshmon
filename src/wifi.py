__doc__ = """
/proc/net/wireless parser module
Version 0.1 - Jerry Chong <zanglang@gmail.com>
"""

import re, sys

def parse(text):
	""" Parse a text block in /proc/net/wireless format and format it into
		an array to be processed.
	:param text: Block of plain text"""

	# Inter-|sta-|  Quality       | Discarded packets             |Missed|WE
	#  face |tus |link level noise|nwid  crypt  frag  retry   misc|beacon|22
	# wlan0: 0000  76   209   160     0      0      0     0     0       0

	pattern = re.compile('(\w{3,4}\d):\s+' # interface
			'\d+\s+'	# status - ignored
			'(\d+)\.?\s+'	# link
			'(\d+)\.?\s+'	# signal
			'(\d+)\.?'		# noise
			'.*') 		# rest of string not used/ignored

	# digest text file into to grab the numbers
	entries = {}
	
	for line in text.split('\n'):

		line = line.strip()
		result = pattern.match(line)
		if result is None:
			continue

		entry = result.groups()
		entries[entry[0]] = ({
			'link': int(entry[1]),
			'signal': int(entry[2]),
			'noise': int(entry[3])
		})

	return entries


#------------------------------------------------------------------------------
def parse_wireless_file(filename):
	""" Read /proc file contents for wireless tools information
	:param filename: Path to file containing wireless metadata """
	try:
		f = open(filename)
	except IOError:
		print 'Could not open ' + filename + ', aborting!'
		return None

	# skip the first two lines/file descriptive header
	f.readline()
	f.readline()

	# read contents of file and pass to the parsing function
	text = f.read()
	entries = parse(text.strip())
	f.close()
	
	print entries	
	return entries


#------------------------------------------------------------------------------
if __name__ == "__main__":
	# first argument as file to read
	filename = len(sys.argv) > 1 and sys.argv[1] \
			or '/proc/net/wireless' # default test file
	print(parse_wireless_file(filename))