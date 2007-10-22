__doc__ = """
MeshMon internal webserver
Version 0.1 - Jerry Chong <zanglang@gmail.com>
"""

import thread, web
import config

render = web.template.render('html/')

urls = (
	'/', 'index',
	'/config.js', 'configure_js' 
)

class index:
	""" Index page for web.py """
	def GET(self):
		#print "Hello, world!"
		print render.index('t')

class configure_js:
	""" Javascript generator. The web interface will parse this script
		to determine which images to show on runtime """
	def GET(self):
		# array for images we will be generating
		files = map(lambda node: [config.ImgPath + '/' + node.address + '-' +
								interface + '.' + config.ImgFormat.lower()
								for interface in node.interfaces],
								nodes.collection)		
		print 'files = ["', '","'.join(files), '"]"'
		print 'interval =', str(config.TrafficInterval * 1000)
		
def start():
	""" Start internal webserver """
	
	# use web.py's error debugging
	web.webapi.internalerror = web.debugerror
	
	# check if the default port has been changed
	if config.WebServerPort != 8080:
		import sys
		sys.argv.append(str(config.WebServerPort))
	
	# Not using meshmon's own threads implementation because web.py's API
	# does not provide methods to kill the webserver. We'll just terminate upon
	# sys.exit() then.
	#thread.start_new_thread(web.run, (urls, globals()))
	web.run(urls, globals())
	
if __name__ == "__main__":
	start()