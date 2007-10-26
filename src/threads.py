__doc__ = """
MeshMon threading functions
Version 0.1 - Jerry Chong <zanglang@gmail.com>
"""

from threading import Thread
import config, logging, time, traceback

pool = []	# Pool for managing multiple threads


#------------------------------------------------------------------------------
class GenericThread(Thread):
	""" Generic manageable thread implementation """
	def __init__(self):
		super(GenericThread, self).__init__()
		self.func = self.__dummy_func		# killwait = whether terminating, whether to wait
		# for it to finish processing
		self.killwait = False

	def run(self):
		""" Run thread """
		try:
			self.func()
		except Exception, e:
			traceback.print_exc()
			logging.error(str(self) + ' stopped abnormally')

	def __dummy_func(self):
		""" Override this! """
		print 'noop'



class MonitorThread(GenericThread):
	""" Generic monitoring thread implementation """
	def __init__(self):
		super(MonitorThread, self).__init__()
		self.interval = 60	# dummy interval
		self.run_flag = 1
		self.killwait = True

	def run(self):
		""" Run thread """
		try:
			while self.run_flag == 1:
				self.func()
				time.sleep(self.interval)
		except Exception, e:
			traceback.print_exc()
			logging.error(str(self) + ' stopped abnormally')


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
		# if thread does not need us to wait
		if not thread.killwait:
			continue
		logging.debug('Terminating thread ' + str(thread))
		thread.run_flag = 0
		#sleep(1)
		if wait:
			try: thread.join()
			except: pass


def size():
	""" Returns number of threads in pool """
	return len(pool)
