if __name__ == '__main__':
    import logging.config
    logging.config.fileConfig("logging.conf")

import thread, time
import logging
import wx
import wx.lib.newevent
from copy import copy

log = logging.getLogger(__name__)

(LineReadEvent, EVT_LINE_READ) = wx.lib.newevent.NewEvent()

class FileReader():
    def __init__(self, filename, window=None, max_lines = 100):
        self.filename = filename
        self.keepGoing = self.running = True
        self.window = window
        self.max_lines = max_lines

    def Start(self):
        self.thread_id = thread.start_new_thread(self.Run, ())
        log.debug("thread %x started" % self.thread_id)

    def Stop(self):
        self.keepGoing = False

    def IsRunning(self):
        return self.running

    def Run(self):
        f = open(self.filename, 'r')
        while self.keepGoing:
            line_queue = []
            line = f.readline()
            while line != "":
                line_queue.append(copy(line))
                if len(line_queue) > self.max_lines:
                    line_queue.pop(0)
                line = f.readline()

            #~ log.debug("foo?")
            for line in line_queue:
                log.debug(line)
                if self.window:
                    evt = LineReadEvent(line=line)
                    wx.PostEvent(self.window, evt)


            log.debug("Wait, read: %s" % len(line_queue))
            time.sleep(1)

        f.close()
        self.running = False


if __name__ == '__main__':
    log.debug("Start")
    #~ t = FileReader('/tmp/logcat.log', max_lines = 3)
    t = FileReader('var/moblock-input.log', max_lines = 3)
    t.Start()
    #~ t.Run()
    time.sleep(5)
    log.debug("Exit")
