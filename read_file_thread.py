if __name__ == '__main__':
    import logging.config
    logging.config.fileConfig("logging.conf")

import thread, time
import logging
import wx
import wx.lib.newevent

log = logging.getLogger(__name__)

(LineReadEvent, EVT_LINE_READ) = wx.lib.newevent.NewEvent()

class FileReader():
    def __init__(self, filename, window=None):
        self.filename = filename
        self.keepGoing = self.running = True
        self.window = window

    def Start(self):
        thread.start_new_thread(self.Run, ())

    def Stop(self):
        self.keepGoing = False

    def IsRunning(self):
        return self.running

    def Run(self):
        f = open(self.filename, 'r')
        while self.keepGoing:
            line = f.readline()
            while line != "":
                log.debug(line)

                evt = LineReadEvent(line=line)
                wx.PostEvent(self.window, evt)

                line = f.readline()

            log.debug("Wait")
            time.sleep(1)

        f.close()
        self.running = False


if __name__ == '__main__':
    log.debug("Start")
    t = FileReader('/tmp/logcat.log')
    t.Start()
    #~ t.Run()
    time.sleep(5)
    log.debug("Exit")
