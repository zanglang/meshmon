__doc__ = """
MeshMon internal webserver
Version 0.1 - Jerry Chong <zanglang@gmail.com>
"""

import os, sys, thread
import web, web.request, web.wsgi, web.webapiimport config, logging, nodes, threads

render = web.template.render('html/', cache=False)

urls = (
	'/', 'index',
	'/update', 'update',
	'/web/(.*)', 'webstuff',
	'/(.*\.css)', 'webstuff',
	'/(.*\.js)', 'webstuff',
	'/images/(.*)', 'images'
)

# definitions for views
TRAFFIC, WIRELESS = range(2)
config.WebView = TRAFFIC	# Default = traffic



class index:
	""" Index page for web.py """

	def GET(self):
		""" Index page generator. The web interface will parse this script
			to determine which images to show on runtime """

		# get list of RRD images
		try:
			files = reduce(lambda files, f: files + f,
				[n.rrd_files.values() for n in nodes.collection
						if n.type is nodes.ROUTER], [])
		except Exception, e:
			# rrd files may not be populated yet
			logging.error(e)
			files = []

		for index, f in enumerate(files):
			if config.WebView is TRAFFIC:
				files[index] = f.replace('.rrd', '')
			else:
				files[index] = f.replace('.rrd', '-wifi')
		files.sort()

		# javascript update interval
		if config.TrafficInterval < 3:
			interval = 3000
		else:
			interval = int(config.TrafficInterval) * 1000

		# read overlib HTML fragment
		f = open('html/weathermap.html')
		imagemap = f.read()
		f.close()

		print render.index(files, interval, imagemap)


class images:
	""" Images loader """
	def GET(self, filename):
		image = os.path.join(config.ImgPath, filename)
		if os.path.exists(image):
			web.header("Cache-Control", "no-cache, must-revalidate")
			print open(image, 'rb').read()
		else:
			web.notfound()


class webstuff:
	""" Static web files loader """
	def GET(self, filename):
		try:
			print open('html/' + filename, 'r').read()
		except:
			web.notfound()


class update:
	""" Handle updating of parameters from form """
	def POST(self):
		i = web.input()

		# Refresh interval is being changed
		if i.has_key('interval'):
			config.TrafficInterval = int(i.interval) / 1000
			# update current threads in pool
			for t in threads.pool:
				t.interval = config.TrafficInterval

		# Page look is being changed
		if i.has_key('view'):
			config.WebView = int(i.view)
			if config.WebView < 0 or config.WebView > WIRELESS:
				config.WebView = TRAFFIC

		if i.has_key('weathermap'):
			config.ShowBandwidthLabel = i.weathermap

		if config.Debug:
			web.debug(i)

		# redirect back to index page
		web.seeother('/')


class WebThread(threads.GenericThread):
	def __init__(self):
		super(WebThread, self).__init__()
		self.func = self.run_web

	def run_web(self):
		""" Start internal webserver """

		# use web.py's error debugging
		web.webapi.internalerror = web.debugerror

		# HACK: check if the default port has been changed to work around
		# web.py's insistence to hard-read the arguments list
		argv = None
		if config.WebServerPort != 8080:
			if len(sys.argv) > 1:
				argv = sys.argv[1]
				sys.argv[1] = str(config.WebServerPort)
			else:
				sys.argv.append(str(config.WebServerPort))

		# Not using meshmon's own threads implementation because web.py's API
		# does not provide methods to kill the webserver. We'll just terminate
		# upon sys.exit() then.
		#thread.start_new_thread(web.run, (urls, globals()))
		web.run(urls, globals(), web.reloader)
		#web.httpserver.runsimple(web.webapi.wsgifunc(web.webpyfunc(urls, globals(), True), web.reloader), ('0.0.0.0', config.WebServerPort))

		# HACK: put argv back
		if argv:
			if len(sys.argv) > 1:
				sys.argv[1] = argv
			else:
				sys.argv.pop()


if __name__ == "__main__":
	web.run(urls, globals())