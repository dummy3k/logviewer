if __name__ == '__main__':
    import logging.config
    logging.config.fileConfig("logging.conf")

import thread, time
import threading
import logging
import os
import wx
import wx.lib.newevent
from copy import copy

log = logging.getLogger(__name__)

(LineReadEvent, EVT_LINE_READ) = wx.lib.newevent.NewEvent()

class FileReader(threading.Thread):
    def __init__(self, filename, window, start_pos):
        threading.Thread.__init__(self)
        self.filename = filename
        self.__keepGoing__ = self.running = True
        self.window = window
        self.pos = start_pos
        self.lock = threading.Lock()

    #~ def Start(self):
        #~ self.thread_id = thread.start_new_thread(self.Run, ())
        #~ log.debug("thread %x started" % self.thread_id)
#~
    #~ def Stop(self):
        #~ self.keepGoing = False
#~
    #~ def IsRunning(self):
        #~ return self.running

    def stop(self):
        self.lock.acquire()
        self.__keepGoing__ = False
        self.lock.release()

    def run(self):
        f = open(self.filename, 'r')
        file_stats = os.fstat(f.fileno())
        if self.pos < 0:
            log.debug("read from the beginning")
            f.seek(file_stats.st_size)
        elif self.pos <= file_stats.st_size:
            log.debug("resuming '%s' at %s" % (self.filename, self.pos))
            f.seek(self.pos)

        keepGoing = True
        while keepGoing:
            line_queue = []
            line = f.readline()
            while line != "":
                if self.window:
                    evt = LineReadEvent(line=line)
                    wx.PostEvent(self.window, evt)

                log.debug(line)
                #~ line_queue.append(copy(line))
                #~ if len(line_queue) > self.max_lines:
                    #~ line_queue.pop(0)
                line = f.readline()

            #~ log.debug("foo?")
            #~ for line in line_queue:
                #~ log.debug(line)
                #~ if self.window:
                    #~ evt = LineReadEvent(line=line)
                    #~ wx.PostEvent(self.window, evt)


            log.debug("Wait, read: %s" % len(line_queue))
            time.sleep(1)

            self.lock.acquire()
            keepGoing = self.__keepGoing__
            self.pos = f.tell()
            self.lock.release()

        f.close()
        self.running = False

if __name__ == '__main__':
    log.debug("Start")
    #~ t = FileReader('/tmp/logcat.log', max_lines = 3)
    t = FileReader('var/moblock-input.log', max_lines = 3)
    t.start()
    #~ t.Run()
    time.sleep(5)
    log.debug("Exit")
