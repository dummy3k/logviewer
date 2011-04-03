if __name__ == '__main__':
    import logging.config
    logging.config.fileConfig("logging.conf")

import time
import multiprocessing
#~ import threading
import logging
import os, sys
import wx
import wx.lib.newevent
from copy import copy

log = logging.getLogger(__name__)

(LineReadEvent, EVT_LINE_READ) = wx.lib.newevent.NewEvent()

#~ class ReadFileThread(threading
def read_file(filename, window, pos):
    f = open(filename, 'r')
    file_stats = os.fstat(f.fileno())
    log.debug("file length: %s" % file_stats.st_size)
    if pos.value < 0:
        pos.value = file_stats.st_size
        f.seek(pos.value)
    elif pos.value <= file_stats.st_size:
        log.info("resuming file '%s' at: %s" % (filename, pos.value))
        f.seek(pos.value)

    while True:
        line_queue = []
        line = f.readline()
        while line != "":
            #~ line_queue.append(copy(line))
            #~ if len(line_queue) > max_lines:
                #~ line_queue.pop(0)

            log.debug(line)
            if window:
                log.debug("Posting event")
                evt = LineReadEvent(line=line)
                wx.PostEvent(window, evt)
                #~ wx.YieldIfNeeded()
                #~ window.AddPendingEvent(evt)

            line = f.readline()
            pos.value = f.tell()

        #~ for line in line_queue:
            #~ if window:
                #~ evt = LineReadEvent(line=line)
                #~ wx.PostEvent(window, evt)


        log.debug("Wait, read: %s" % len(line_queue))
        time.sleep(1)

    f.close()

def create_process(filename, window, start_pos):
    pos = multiprocessing.Value('i', start_pos)
    p = multiprocessing.Process(target=read_file,
                                args=(filename, window, pos))
    return (p, pos)

if __name__ == '__main__':
    log.debug("Start")
    if len(sys.argv) < 2:
        start_pos = -1
    else:
        start_pos = int(sys.argv[1])

    t, pos = create_process('/tmp/logcat.log', None, start_pos)
    t.start()
    log.debug("Wating 5s")
    time.sleep(5)

    #~ log.debug("pos: %s" % pos.value)
    #~ log.debug("Wating 5s")
    #~ time.sleep(10)

    t.terminate()
    log.debug("Exit: %s" % pos.value)
