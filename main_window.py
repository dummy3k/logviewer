import logging
import re, os
import wx
import wx.lib.mixins.listctrl  as  listmix
import libxml2

from read_file_thread import FileReader, EVT_LINE_READ
from read_file_project import ReadFileProject

if __name__ == '__main__':
    import logging.config
    logging.config.fileConfig("logging.conf")

log = logging.getLogger(__name__)

class TreeItemData():
    def __init__(self, list_view):
        self.list_view = list_view

    def OnSelChanged(self, event):
        log.debug("TreeItemData.OnSelChanged()")
        self.list_view.SetColumns([])

class ProjectTreeItemData(TreeItemData):
    def __init__(self, project, list_view):
        TreeItemData.__init__(self, list_view)
        self.project = project

    def OnSelChanged(self, event):
        log.debug("ProjectTreeItemData.OnSelChanged()")
        self.list_view.SetColumns(self.project.parameters)
        for item in self.project.get_last(MyFrame.MAX_LIST_ITEMS):
            item_id = self.list_view.Append(item[1:])
            log.debug(item_id)

        self.list_view.FitAndMoveLast()

class LoggerInfoItemData(TreeItemData):
    def __init__(self, logger_info, list_view):
        TreeItemData.__init__(self, list_view)
        self.logger_info = logger_info

    #~ def OnSelChanged(self, event):
        #~ log.debug("LoggerInfoItemData.OnSelChanged()")


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

    def SetColumns(self, col_names):
        #~ log.debug("LogLinesListCtrlPanel.SetColumns")
        self.DeleteAllItems()
        self.DeleteAllColumns()
        for index, name in enumerate(col_names):
            self.InsertColumn(index, name)

    def FitAndMoveLast(self):
        for index in range(self.GetColumnCount()):
            self.SetColumnWidth(index, wx.LIST_AUTOSIZE)
        self.EnsureVisible(self.GetItemCount() - 1)

class MyFrame(wx.Frame):
    WINDOW_XML_FILENAME = 'var/window.xml'
    MAX_LIST_ITEMS = 100

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

        self.tree = wx.TreeCtrl(self.splitter, wx.ID_ANY, wx.DefaultPosition,
                           wx.DefaultSize, wx.TR_DEFAULT_STYLE)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.TreeOnSelChanged, self.tree)

        self.list_view = LogLinesListCtrlPanel(self.splitter)

        self.splitter.SetMinimumPaneSize(20)
        self.splitter.SplitVertically(self.tree, self.list_view, 240)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_CLOSE, self.OnFormClose)

        self.tree.Bind(EVT_LINE_READ, self.OnUpdate)
        self.projects = {}
        root = self.tree.AddRoot("LogViewer")

        self.LoadProject('logcat.logproj')
        self.LoadProject('moblock.logproj')

        if os.path.exists(MyFrame.WINDOW_XML_FILENAME):
            doc = libxml2.parseFile(MyFrame.WINDOW_XML_FILENAME)
            root = doc.firstElementChild()
            left = root.prop('left')
            top = root.prop('top')
            self.SetPosition((int(left), int(top)))

            width = root.prop('width')
            height = root.prop('height')
            self.SetSize((int(width), int(height)))

    def OnSize(self, event):
        w,h = self.GetClientSizeTuple()
        self.splitter.SetDimensions(0, 0, w, h)

    def MenuMarkAllAsRead(self, event):
        for project in self.projects.values():
            for loginfo in project.logger_infos.values():
                loginfo.MarkAsRead()

    def OnFormClose(self, event):
        log.debug("OnFormClose(CanVeto: %s)" % event.CanVeto())
        doc = libxml2.newDoc('1.0')
        root = doc.newChild(None, 'window', None)

        left, top = self.GetPosition()
        root.setProp('top', str(top))
        root.setProp('left', str(left))

        width, height = self.GetSize()
        root.setProp('width', str(width))
        root.setProp('height', str(height))

        log.debug("XML: %s" % doc.serialize())
        doc.saveFile(MyFrame.WINDOW_XML_FILENAME)

        event.Skip()

    def MenuNewProject(self, event):
        pass

    def LoadProject(self, filename):
        project = ReadFileProject(self.tree, xml_filename=filename)
        self.projects[project.get_id()] = project

        if self.tree.GetChildrenCount(self.tree.GetRootItem()) == 1:
            self.tree.Expand(self.tree.GetRootItem())

        self.tree.SetPyData(project.root, ProjectTreeItemData(project, self.list_view))

    def TreeOnSelChanged(self, event):
        item_id = event.GetItem()
        if not item_id:
            return

        item_data = self.tree.GetPyData(item_id)
        if not item_data:
            log.warn("Tree node without item data")
            return

        log.debug("TreeOnSelChanged(%s)" % item_data)
        item_data.OnSelChanged(event)

    def TreeOnSelChanged_old(self, event):
        log.debug("TreeOnLeftDClick()")
        item_id = event.GetItem()
        if item_id:
            loginfo = self.tree.GetPyData(item_id)
            if loginfo:
                log.debug("OnSelChanged: %s\n" % loginfo)

                self.list_view.DeleteAllItems()

                self.list_view.DeleteAllColumns()
                log.debug("loginfo.parameters: %s" % loginfo.parameters)
                for index, name in enumerate(loginfo.parameters):
                    self.list_view.InsertColumn(index, name)

                last_item_idx = 0
                for row in loginfo.messages[-MyFrame.MAX_LIST_ITEMS:]:
                    try:
                        log.debug(row)
                        last_item_idx = self.list_view.Append(row)
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
        for project in self.projects.values():
            match = project.line_filter.match(event.line.strip())
            if match:
                param_values = match.groups()
                project.append(param_values)

                #~ log.debug(match.groups())
                logger_name = param_values[project.group_by]
                if not logger_name in project.logger_infos:
                    #~ log.debug("New logger_name: %s" % logger_name)
                    child = self.tree.AppendItem(project.root, logger_name)
                    loginfo = LoggerInfo(logger_name, child, self.tree, project.parameters)
                    #~ self.tree.SetPyData(child, loginfo)
                    self.tree.SetPyData(child, LoggerInfoItemData(loginfo, self.list_view))
                    project.logger_infos[logger_name] = loginfo
                    if self.tree.GetChildrenCount(project.root) == 1:
                        self.tree.Expand(project.root)

                loginfo = project.logger_infos[logger_name]
                loginfo.messages.append(param_values)

                #~ focused_loginfo = self.tree.GetPyData(self.tree.GetSelection())
                #~ if focused_loginfo and focused_loginfo.name == logger_name:
                    #~ log.debug("Focused!")
                    #~ try:
                        #~ pos = self.list_view.Append(param_values)
                        #~ self.list_view.EnsureVisible(pos)
                    #~ except UnicodeDecodeError:
                        #~ log.error("UnicodeDecodeError in TreeOnSelChanged()")
                #~ else:
                    #~ loginfo.MarkAsUnRead()

                return

        log.error("failed match '%s'" % event.line)

def main():
    app = wx.App()
    win = MyFrame(None, pos=(0,0), size=(1024, 800))
    win.Show()

    log.info("entering main loop")
    app.MainLoop()

if __name__ == '__main__':
    main()
