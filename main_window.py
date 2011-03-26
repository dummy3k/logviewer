import logging
import re, os
import wx
import wx.lib.mixins.listctrl  as  listmix

from read_file_thread import FileReader, EVT_LINE_READ

if __name__ == '__main__':
    import logging.config
    logging.config.fileConfig("logging.conf")

log = logging.getLogger(__name__)
MAX_LIST_ITEMS = 100

class LoggerInfo():
    def __init__(self, name, tree_node):
        self.name = name
        self.unread_count = 0
        self.tree_node = tree_node
        self.messages = []

    def __str__(self):
        return "LoggerInfo('%s', %s)" % (self.name, self.unread_count)

class LogLinesListCtrlPanel(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1, style=wx.WANTS_CHARS | wx.LC_REPORT)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

class MyFrame(wx.Frame):
    def __init__(
            self, parent, ID=wx.ID_ANY, title="Map the Internet",
            pos=wx.DefaultPosition,
            size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE
            ):

        wx.Frame.__init__(self, parent, ID, title, pos, size, style)
        self.logger_infos = {}
        self.splitter = wx.SplitterWindow(self)

        menuBar = wx.MenuBar()
        menu1 = wx.Menu()
        menu1.Append(101, "&Mercury", "This the text in the Statusbar")
        menuBar.Append(menu1, "&Planets")
        self.SetMenuBar(menuBar)

        filename = '/tmp/logcat.log'
        self.tree = wx.TreeCtrl(self.splitter, wx.ID_ANY, wx.DefaultPosition,
                           wx.DefaultSize, wx.TR_DEFAULT_STYLE)
        self.root = self.tree.AddRoot(os.path.basename(filename))
        #~ self.tree.Bind(wx.EVT_LEFT_DCLICK, self.TreeOnLeftDClick)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.TreeOnSelChanged, self.tree)

        self.list_view = LogLinesListCtrlPanel(self.splitter)
        self.list_view.InsertColumn(0, "level")
        self.list_view.InsertColumn(1, "logger_name")
        self.list_view.InsertColumn(2, "thread_id", wx.LIST_FORMAT_RIGHT)
        self.list_view.InsertColumn(3, "message")
        #~ self.list_view.Append(('level', 'logger_name', 'thread_id', 'message'))

        self.splitter.SetMinimumPaneSize(20)
        self.splitter.SplitVertically(self.tree, self.list_view, 240)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.OnSashChanging)
        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGING, self.OnSashChanging)

        self.reader = FileReader(filename, self)
        self.Bind(EVT_LINE_READ, self.OnUpdate)
        self.reader.Start()

    def OnSize(self, event):
        w,h = self.GetClientSizeTuple()
        self.splitter.SetDimensions(0, 0, w, h)

    def OnSashChanging(self, event):
        log.debug("sash changing to %s\n" % str(event.GetSashPosition()))

    def TreeOnSelChanged(self, event):
        log.debug("TreeOnLeftDClick()")
        item_id = event.GetItem()
        if item_id:
            loginfo = self.tree.GetPyData(item_id)
            log.debug("OnSelChanged: %s\n" % loginfo)

            self.list_view.DeleteAllItems()
            for row in loginfo.messages[-MAX_LIST_ITEMS:]:
                try:
                    self.list_view.Append(row)
                except UnicodeDecodeError:
                    log.error("UnicodeDecodeError in TreeOnSelChanged()")

            loginfo.unread_count = 0
            #~ log.debug("%s.unread_count: %s" % (logger_name, loginfo.unread_count))
            self.tree.SetItemText(loginfo.tree_node, loginfo.name)

        event.Skip()

    def OnUpdate(self, event):
        #~ log.debug("got line: %s" % event.line)
        match = re.match("(\\w)/([-\\w\\./]+) *\\( *(\\d+)\\): (.*)", event.line.strip())
        if not match:
            log.error("failed match '%s'" % event.line)
            return

        level, logger_name, thread_id, message = match.groups()
        #~ log.debug(match.groups())
        if not logger_name in self.logger_infos:
            #~ log.debug("New logger_name: %s" % logger_name)
            child = self.tree.AppendItem(self.root, logger_name)
            loginfo = LoggerInfo(logger_name, child)
            self.tree.SetPyData(child, loginfo)
            self.logger_infos[logger_name] = loginfo
            if len(self.logger_infos) == 1:
                self.tree.Expand(self.root)

        loginfo = self.logger_infos[logger_name]
        loginfo.unread_count += 1
        #~ log.debug("%s.unread_count: %s" % (logger_name, loginfo.unread_count))
        self.tree.SetItemText(loginfo.tree_node,
            "%s (%s)" % (logger_name, loginfo.unread_count))
        loginfo.messages.append((level, logger_name, thread_id, message))

def main():
    app = wx.App()
    win = MyFrame(None, pos=(0,0), size=(1024, 800))
    win.Show()

    log.info("entering main loop")
    app.MainLoop()

if __name__ == '__main__':
    main()
