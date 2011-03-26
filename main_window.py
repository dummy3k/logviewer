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

class ReadFileProject():
    def __init__(self, *args, **kwargs):
        if 'log_file_name' in kwargs:
            pass
        elif 'log_file_name' in kwargs:
            pass
        else:
            raise TypeError('bad arguments')

    def save_to_file(self, filename):
        pass

class LoggerInfo():
    def __init__(self, name, tree_node, tree_control):
        self.name = name
        self.unread_count = 0
        self.tree_node = tree_node
        self.messages = []
        self.tree = tree_control

    def __str__(self):
        return "LoggerInfo('%s', %s)" % (self.name, self.unread_count)

    def MarkAsUnRead(self):
        self.unread_count += 1
        self.tree.SetItemText(self.tree_node,
            "%s (%s)" % (self.name, self.unread_count))
        self.tree.SetItemBold(self.tree_node, True)

    def MarkAsRead(self):
        self.unread_count = 0
        self.tree.SetItemText(self.tree_node, self.name)
        self.tree.SetItemBold(self.tree_node, False)

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
        menuItem = wx.Menu()
        menuItem.Append(wx.ID_ANY, "&Mark all as read")
        menuBar.Append(menuItem, "&Messages")
        self.Bind(wx.EVT_MENU, self.MenuMarkAllAsRead)
        self.SetMenuBar(menuBar)

        filename = '/tmp/logcat.log'
        self.tree = wx.TreeCtrl(self.splitter, wx.ID_ANY, wx.DefaultPosition,
                           wx.DefaultSize, wx.TR_DEFAULT_STYLE)
        self.root = self.tree.AddRoot(os.path.basename(filename))
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.TreeOnSelChanged, self.tree)

        self.list_view = LogLinesListCtrlPanel(self.splitter)
        self.list_view.InsertColumn(0, "level")
        self.list_view.InsertColumn(1, "logger_name")
        self.list_view.InsertColumn(2, "thread_id", wx.LIST_FORMAT_RIGHT)
        self.list_view.InsertColumn(3, "message")

        self.splitter.SetMinimumPaneSize(20)
        self.splitter.SplitVertically(self.tree, self.list_view, 240)
        self.Bind(wx.EVT_SIZE, self.OnSize)

        self.reader = FileReader(filename, self)
        self.Bind(EVT_LINE_READ, self.OnUpdate)
        self.reader.Start()

    def OnSize(self, event):
        w,h = self.GetClientSizeTuple()
        self.splitter.SetDimensions(0, 0, w, h)

    def MenuMarkAllAsRead(self, event):
        for loginfo in self.logger_infos.values():
            loginfo.MarkAsRead()

    def TreeOnSelChanged(self, event):
        log.debug("TreeOnLeftDClick()")
        item_id = event.GetItem()
        if item_id:
            loginfo = self.tree.GetPyData(item_id)
            log.debug("OnSelChanged: %s\n" % loginfo)

            self.list_view.DeleteAllItems()
            last_item_idx = 0
            for row in loginfo.messages[-MAX_LIST_ITEMS:]:
                try:
                    last_item_idx = self.list_view.Append(row)
                except UnicodeDecodeError:
                    log.error("UnicodeDecodeError in TreeOnSelChanged()")

            loginfo.MarkAsRead()
            self.list_view.EnsureVisible(last_item_idx)

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
            loginfo = LoggerInfo(logger_name, child, self.tree)
            self.tree.SetPyData(child, loginfo)
            self.logger_infos[logger_name] = loginfo
            if len(self.logger_infos) == 1:
                self.tree.Expand(self.root)

        loginfo = self.logger_infos[logger_name]
        loginfo.messages.append((level, logger_name, thread_id, message))

        focused_loginfo = self.tree.GetPyData(self.tree.GetSelection())
        if focused_loginfo and focused_loginfo.name == logger_name:
            log.debug("Focused!")
            try:
                pos = self.list_view.Append((level, logger_name, thread_id, message))
                self.list_view.EnsureVisible(pos)
            except UnicodeDecodeError:
                log.error("UnicodeDecodeError in TreeOnSelChanged()")
        else:
            loginfo.MarkAsUnRead()

def main():
    app = wx.App()
    win = MyFrame(None, pos=(0,0), size=(1024, 800))
    win.Show()

    log.info("entering main loop")
    app.MainLoop()

if __name__ == '__main__':
    main()
