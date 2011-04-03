if __name__ == '__main__':
    import logging.config
    logging.config.fileConfig("logging.conf")

import thread, time
import threading
import logging
import os, sys
import pickle
import wx
import wx.lib.newevent
from copy import copy

log = logging.getLogger(__name__)

(LineReadEvent, EVT_LINE_READ) = wx.lib.newevent.NewEvent()

class FileReader(threading.Thread):
    def __init__(self, filename, pos_filename, window):
        threading.Thread.__init__(self)
        self.filename = filename
        self.__keepGoing__ = self.running = True
        self.window = window
        self.lock = threading.Lock()
        self.pos_filename = pos_filename

        if not os.path.exists(pos_filename):
            log.debug("%s does not exists" % pos_filename)
            self.pos = -1
        else:
            with open(pos_filename, 'rb') as f:
                self.pos = pickle.load(f)
                f.close()
            log.info("resuming '%s' at %s" % (self.filename, self.pos))

    def stop(self):
        self.lock.acquire()
        self.__keepGoing__ = False
        self.lock.release()

    def run(self):
        keepGoing = True
        while keepGoing:
            f = open(self.filename, 'r')
            file_stats = os.fstat(f.fileno())
            if self.pos < 0:
                #~ log.debug("read from the beginning")
                f.seek(file_stats.st_size)
            elif self.pos <= file_stats.st_size:
                f.seek(self.pos)

            line = f.readline()
            while line != "":
                if f.closed:
                    log.warn("file is closed")

                file_stats = os.fstat(f.fileno())
                if f.tell() > file_stats.st_size:
                    log.warn("file trimmed")


                if self.window:
                    evt = LineReadEvent(line=line)
                    wx.PostEvent(self.window, evt)

                log.debug(line)
                line = f.readline()


            file_stats = os.fstat(f.fileno())
            log.debug("Wait, tell: %s, size: %s" % (f.tell(), file_stats.st_size))
            time.sleep(1)

            self.lock.acquire()
            keepGoing = self.__keepGoing__
            self.pos = f.tell()
            self.lock.release()

            with open(self.pos_filename, 'wb') as f:
                pickle.dump(self.pos, f)
                f.close()

            f.close()

        self.running = False

if __name__ == '__main__':
    log.debug("Start")
    #~ t = FileReader('/tmp/logcat.log', max_lines = 3)
    if len(sys.argv) > 1:
        start_pos = int(sys.argv[1])
    else:
        start_pos = -1

    t = FileReader('/tmp/logcat.log', 'var/logcat.pos-test', None)
    log.debug("t.pos: %s" % t.pos)
    t.start()
    try:
        while True:
            log.debug("waiting")
            time.sleep(5)
    except KeyboardInterrupt:
        pass

    log.debug("stopping thread...")
    t.stop()
    t.join()

    log.debug("Exit: %s" % t.pos)
