__doc__ = """
MeshMon threading functions
Version 0.1 - Jerry Chong <zanglang@gmail.com>
"""

from threading import Thread
import logging, time, traceback

if (config.Debug):
	logging.basicConfig(level=logging.DEBUG)
	
pool = []	# Pool for managing multiple threads

#------------------------------------------------------------------------------ 
class MonitorThread(Thread):
	""" Generic monitoring thread implementation """
	def __init__(self):
		super(MonitorThread, self).__init__()
		self.interval = 60	# dummy interval
		self.func = self.__dummy_func
		self.run_flag = 1
		
	def run(self):
		""" Run thread """
		try:
			while self.run_flag == 1:
				self.func()
				time.sleep(self.interval)
		except Exception, e:
			traceback.print_exc()
			logging.error('Thread stopped abnormally')
		
	def __dummy_func(self):
		""" Override this! """
		print 'noop'

#------------------------------------------------------------------------------ 
def add(thread, run=True):
	""" Add a thread to the global thread pool.
	:param run: Whether to start the thread automatically (default: True) """
	logging.debug('Adding thread ' + str(thread))
	pool.append(thread)
	if run:
		thread.start()

def terminate_all(wait=False):
	""" Signal to terminate all threads in the pool
	:param wait: Whether to wait until all threads have terminated (default: False) """
	for thread in pool:
		logging.debug('Terminating thread ' + str(thread))
		thread.run_flag = 0
		#sleep(1)
		if wait:
			try: thread.join()
			except: pass

def len():
	""" Returns number of threads in pool """
	return len(pool)