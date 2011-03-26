import wx
import logging
import re, os

from read_file_thread import FileReader, EVT_LINE_READ

if __name__ == '__main__':
    import logging.config
    logging.config.fileConfig("logging.conf")

log = logging.getLogger(__name__)

class LoggerInfo():
    def __init__(self, name, tree_node):
        self.name = name
        self.unread_count = 0
        self.tree_node = tree_node

class MyFrame(wx.Frame):
    def __init__(
            self, parent, ID=wx.ID_ANY, title="Map the Internet",
            pos=wx.DefaultPosition,
            size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE
            ):

        wx.Frame.__init__(self, parent, ID, title, pos, size, style)
        self.logger_infos = {}
        self.Bind(wx.EVT_SIZE, self.OnSize)

        menuBar = wx.MenuBar()
        menu1 = wx.Menu()
        menu1.Append(101, "&Mercury", "This the text in the Statusbar")
        menuBar.Append(menu1, "&Planets")
        self.SetMenuBar(menuBar)

        filename = '/tmp/logcat.log'
        self.tree = wx.TreeCtrl(self, wx.ID_ANY, wx.DefaultPosition,
                           wx.DefaultSize, wx.TR_DEFAULT_STYLE)
        self.root = self.tree.AddRoot(os.path.basename(filename))


        self.reader = FileReader(filename, self)
        self.Bind(EVT_LINE_READ, self.OnUpdate)
        self.reader.Start()

    def OnSize(self, event):
        w,h = self.GetClientSizeTuple()
        self.tree.SetDimensions(0, 0, w, h)

    def OnUpdate(self, evt):
        #~ log.debug("got line: %s" % evt.line)
        match = re.match("(\\w)/([-\\w\\./]+) *\\( *(\\d+)\\): (.*)", evt.line)
        if not match:
            log.error("failed match '%s'" % evt.line)
            return

        level, logger_name, thread_id, message = match.groups()
        #~ log.debug(match.groups())
        if not logger_name in self.logger_infos:
            log.debug("New logger_name: %s" % logger_name)
            child = self.tree.AppendItem(self.root, logger_name)
            self.logger_infos[logger_name] = LoggerInfo(logger_name, child)
            if len(self.logger_infos) == 1:
                self.tree.Expand(self.root)

        loginfo = self.logger_infos[logger_name]
        loginfo.unread_count += 1
        log.debug("%s.unread_count: %s" % (logger_name, loginfo.unread_count))
        self.tree.SetItemText(loginfo.tree_node,
            "%s (%s)" % (logger_name, loginfo.unread_count))

def main():
    app = wx.App()
    win = MyFrame(None, pos=(0,0), size=(300, 800))
    win.Show()

    log.info("entering main loop")
    app.MainLoop()

if __name__ == '__main__':
    main()
