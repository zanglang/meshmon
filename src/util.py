
__doc__ = """
MeshMon utility functions
Version 0.1 - Jerry Chong <zanglang@gmail.com>
"""

from threading import Thread
from time import sleep
from traceback import print_exc
import config

#------------------------------------------------------------------------------ 
class MonitorThread(Thread):
	"""
	Thread super-class
	"""
	def __init__(self):
		super(MonitorThread, self).__init__()
		self.interval = 60	# dummy interval
		self.func = self.__dummy_func
		self.run_flag = 1
		
	def run(self):
		"""Run thread"""
		try:
			while self.run_flag == 1:
				self.func()
				sleep(self.interval)
		except Exception, e:
			print_exc()
			print 'Thread stopped abnormally'
			pass
		
	def __dummy_func(self):
		print 'noop'

#------------------------------------------------------------------------------ 
class _ThreadPool:
	"""
	Thread pool
	"""	
	__instance = None
	
	def __init__(self):
		self.__pool = []
	
	def add(self, thread):
		"""Add a thread to the pool"""
		self.__pool.append(thread)
	
	def get(self):
		"""Directly access the pool"""
		return self.__pool
	
	def terminate(self):
		"""Signal to terminate all threads in the pool"""
		for thread in self.__pool:
			thread.run_flag = 0
			sleep(1)
			#try: thread.join()
			#except: pass
	
	def len(self):
		"""Number of threads in pool"""
		return len(self.__pool)	

# pool instance
__thread_pool = _ThreadPool()

def ThreadPool():
	"""
	Returns a Singleton instance of the threadpool,
	or creating one if necessary
	"""
	# TODO: move to class method
	return __thread_pool

#------------------------------------------------------------------------------ 
def convert_to_js():
	"""
	Outputs current Meshmon configuration into Javascript
	"""
	
	# array for images we will be generating
	files = [config.ImgPath + '/' + node + '-' + interface + '.' +
											config.ImgFormat.lower()
			for node in config.Nodes
			for interface in config.Interfaces]
	
	# dump into file
	f = open('config.js', 'w')
	f.write("files = ['" + "','".join(files) + "']\n")
	f.write("interval = " + str(config.TrafficInterval * 1000) + "\n")
	f.close()