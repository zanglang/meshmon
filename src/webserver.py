__doc__ = """
MeshMon internal webserver
Version 0.1 - Jerry Chong <zanglang@gmail.com>
"""

import os, thread, web
import config, logging, nodes

render = web.template.render('html/')

urls = (
	'/', 'index',
	'/update', 'update',	'/js/(.*)', 'js',
	'/images/(.*)', 'images',
	'/view/(.*)', 'view'
)


class index:
	""" Index page for web.py """
	def GET(self):
		""" Index page generator. The web interface will parse this script
			to determine which images to show on runtime """		files = map(lambda node: [node.address + '-' + interface + '.' +
											config.ImgFormat.lower()
									for interface in node.interfaces],
									nodes.collection)
		interval = int(config.TrafficInterval) * 1000
		print render.index(files, interval)


class images:
	""" Images loader """
	def GET(self, filename):
		image = os.path.join(config.ImgPath, filename)
		if os.path.exists(image):
			web.header("Cache-Control", "no-cache, must-revalidate")
			print open(image, 'rb').read()
		else:
			web.notfound()
			
			
class js:
	""" Javascript loader """
	def GET(self, filename):
		try:
			print open('html/' + filename, 'r').read()
		except:
			web.notfound()

		
class update:
	""" Handle updating of parameters from form """
	def POST(self):
		i = web.input()
		web.debug(i)
		if i.has_key('interval'):
			config.TrafficInterval = int(i.interval) / 1000
		web.seeother('/')
		

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
	web.run(urls, globals(), web.reloader)


if __name__ == "__main__":
	start()