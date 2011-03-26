import logging
import re, os
import wx
import wx.lib.mixins.listctrl  as  listmix
import libxml2

from read_file_thread import FileReader, EVT_LINE_READ

if __name__ == '__main__':
    import logging.config
    logging.config.fileConfig("logging.conf")

log = logging.getLogger(__name__)
MAX_LIST_ITEMS = 100

class ReadFileProject():
    def __init__(self, *args, **kwargs):
        self.logger_infos = {}
        self.tree = args[0]

        if 'log_file_name' in kwargs:
            pass
        elif 'xml_filename' in kwargs:
            doc = libxml2.parseFile(kwargs['xml_filename'])
            ctxt = doc.xpathNewContext()
            readFileNode = ctxt.xpathEval("/readFile")[0]
            filename = readFileNode.prop('filename')

            pnodes = ctxt.xpathEval("/readFile/lineFilter/parameter")
            self.parameters = map(lambda x: x.prop('name'), pnodes)
            log.debug("self.parameters: %s" % self.parameters)

            lineFilterNode = ctxt.xpathEval("/readFile/lineFilter")[0]
            regex_str = lineFilterNode.prop('regex')
            self.line_filter = re.compile(regex_str)
            self.group_by = int(lineFilterNode.prop('groupBy'))
        else:
            raise TypeError('bad arguments')

        self.root = self.tree.AppendItem(self.tree.GetRootItem(),
                                         os.path.basename(filename))
        self.reader = FileReader(filename, self.tree)
        self.reader.Start()

    def get_id(self):
        return self.reader.thread_id

    def save_to_file(self, filename):
        pass

class LoggerInfo():
    def __init__(self, name, tree_node, tree_control, parameters):
        self.name = name
        self.unread_count = 0
        self.tree_node = tree_node
        self.messages = []
        self.tree = tree_control
        self.parameters = parameters

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
        self.splitter = wx.SplitterWindow(self)

        menuBar = wx.MenuBar()

        menuItem = wx.Menu()
        menuItem.Append(wx.ID_ANY, "&New")
        self.Bind(wx.EVT_MENU, self.MenuNewProject)
        menuBar.Append(menuItem, "&Project")

        menuItem = wx.Menu()
        menuItem.Append(wx.ID_ANY, "&Mark all as read")
        self.Bind(wx.EVT_MENU, self.MenuMarkAllAsRead)
        menuBar.Append(menuItem, "&Messages")

        self.SetMenuBar(menuBar)

        #~ filename = '/tmp/logcat.log'
        self.tree = wx.TreeCtrl(self.splitter, wx.ID_ANY, wx.DefaultPosition,
                           wx.DefaultSize, wx.TR_DEFAULT_STYLE)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.TreeOnSelChanged, self.tree)

        self.list_view = LogLinesListCtrlPanel(self.splitter)
        #~ self.list_view.DeleteAllColumns()
        #~ self.list_view.InsertColumn(0, "level")
        #~ self.list_view.InsertColumn(1, "logger_name")
        #~ self.list_view.InsertColumn(2, "thread_id", wx.LIST_FORMAT_RIGHT)
        #~ self.list_view.InsertColumn(3, "message")

        self.splitter.SetMinimumPaneSize(20)
        self.splitter.SplitVertically(self.tree, self.list_view, 240)
        self.Bind(wx.EVT_SIZE, self.OnSize)

        self.tree.Bind(EVT_LINE_READ, self.OnUpdate)
        self.projects = {}
        root = self.tree.AddRoot("LogViewer")

        self.LoadProject('logcat.logproj')
        self.LoadProject('moblock.logproj')
        #~ self.tree.Expand(root)

    def OnSize(self, event):
        w,h = self.GetClientSizeTuple()
        self.splitter.SetDimensions(0, 0, w, h)

    def MenuMarkAllAsRead(self, event):
        for project in self.projects.values():
            for loginfo in project.logger_infos.values():
                loginfo.MarkAsRead()

    def MenuNewProject(self, event):
        pass

    def LoadProject(self, filename):
        project = ReadFileProject(self.tree, xml_filename=filename)
        self.projects[project.get_id()] = project

        if self.tree.GetChildrenCount(self.tree.GetRootItem()) == 1:
            self.tree.Expand(self.tree.GetRootItem())


    def TreeOnSelChanged(self, event):
        log.debug("TreeOnLeftDClick()")
        item_id = event.GetItem()
        if item_id:
            loginfo = self.tree.GetPyData(item_id)
            if loginfo:
                log.debug("OnSelChanged: %s\n" % loginfo)

                self.list_view.DeleteAllItems()

                self.list_view.DeleteAllColumns()
                for index, name in enumerate(loginfo.parameters):
                    self.list_view.InsertColumn(index, name)

                last_item_idx = 0
                for row in loginfo.messages[-MAX_LIST_ITEMS:]:
                    try:
                        log.debug(row)
                        last_item_idx = self.list_view.Append(row[:4])
                        pass
                    except UnicodeDecodeError:
                        log.error("UnicodeDecodeError in TreeOnSelChanged()")

                loginfo.MarkAsRead()
                for index in range(len(loginfo.parameters)):
                    self.list_view.SetColumnWidth(index, wx.LIST_AUTOSIZE)
                self.list_view.EnsureVisible(last_item_idx)

        event.Skip()

    def OnUpdate(self, event):
        #~ log.debug("got line: %s" % event.line)
        #~ match = re.match("(\\w)/([-\\w\\./]+) *\\( *(\\d+)\\): (.*)", event.line.strip())
        #~ project = self.projects.values()[0]
        for project in self.projects.values():
            match = project.line_filter.match(event.line.strip())
            if match:
                param_values = match.groups()
                #~ log.debug(match.groups())
                logger_name = param_values[project.group_by]
                if not logger_name in project.logger_infos:
                    #~ log.debug("New logger_name: %s" % logger_name)
                    child = self.tree.AppendItem(project.root, logger_name)
                    loginfo = LoggerInfo(logger_name, child, self.tree, project.parameters)
                    self.tree.SetPyData(child, loginfo)
                    project.logger_infos[logger_name] = loginfo
                    if self.tree.GetChildrenCount(project.root) == 1:
                        self.tree.Expand(project.root)

                loginfo = project.logger_infos[logger_name]
                loginfo.messages.append(param_values)

                focused_loginfo = self.tree.GetPyData(self.tree.GetSelection())
                if focused_loginfo and focused_loginfo.name == logger_name:
                    log.debug("Focused!")
                    try:
                        pos = self.list_view.Append(param_values)
                        self.list_view.EnsureVisible(pos)
                    except UnicodeDecodeError:
                        log.error("UnicodeDecodeError in TreeOnSelChanged()")
                else:
                    loginfo.MarkAsUnRead()

                return

        #~ log.error("failed match '%s'" % event.line)

def main():
    app = wx.App()
    win = MyFrame(None, pos=(0,0), size=(1024, 800))
    win.Show()

    log.info("entering main loop")
    app.MainLoop()

if __name__ == '__main__':
    main()
