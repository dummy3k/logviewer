import logging
import re, os
import wx
import libxml2
from copy import copy

if __name__ == '__main__':
    import logging.config
    logging.config.fileConfig("logging.conf")


from read_file_project import ReadFileProject
from read_file_thread import EVT_LINE_READ
from filter import get_filter_class, ParsingFailedError, TrueExpression
from gui import *

log = logging.getLogger(__name__)
log_repeat = logging.getLogger(__name__ + '.repeat')

class NorExpression():
    def __init__(self, expressions):
        self.expressions = expressions

    def eval_values(self, values):
        for item in self.expressions:
            if item.eval_values(values):
                return False
        return True

class TreeItemData():
    def __init__(self, list_view):
        self.list_view = list_view
        self.filter_expression = None
        self.project_id = None

    def OnSelChanged(self, event):
        log.debug("TreeItemData.OnSelChanged()")
        self.list_view.SetColumns([])

    def IncomingMessage(self, msg):
        pass

class ProjectTreeItemData(TreeItemData):
    CNT_READ_AHEAD = 100
    ROW_BUFFER_SIZE = 3 * CNT_READ_AHEAD

    def __init__(self, project, list_view, app_frame, tree_node):
        TreeItemData.__init__(self, list_view)
        self.project = project
        self.rows = {}
        self.last_row_id = None
        self.project_id = project.get_id()
        self.app_frame = app_frame
        self.where_clause = None
        self.__row_cnt__ = None
        self.tree = app_frame.tree
        self.unread_count = 0
        self.name = project.name
        self.tree_node = tree_node
        #~ self.filter_expression = TrueExpression()
        expressions = [x.filter_expression for x in project.filters]
        self.filter_expression = NorExpression(expressions)

    def OnSelChanged(self, event):
        log.debug("ProjectTreeItemData.OnSelChanged()")
        self.MarkAsRead()

        row_count = self.project.get_row_count(self.where_clause)
        log.debug("row_count: %s" % row_count)
        self.app_frame.sb.SetStatus('row_cnt', "Rows: %s" % row_count, True)
        self.__row_cnt__ = int(row_count)
        self.rows = {}

        self.list_view.SaveColumnWidthDict()
        self.list_view.SetColumns(self.project.parameters)
        self.list_view.SetItemCount(row_count)
        self.list_view.OnGetItemTextCallback = self
        self.list_view.Refresh()
        self.list_view.MoveLast()

    def OnGetItemText(self, item, col):
        #~ if col == 0:
            #~ log.debug("ProjectTreeItemData.OnGetItemText(%s, %s)" % (item, col))
        if not self.last_row_id:
            going_up = False
        elif self.last_row_id < item:
            going_up = False
        elif self.last_row_id > item:
            going_up = True
        else:
            going_up = False

        self.last_row_id = item

        if not item in self.rows:
            log.debug("ProjectTreeItemData.OnGetItemText(%s, %s)" % (item, col))
            if len(self.rows) + ProjectTreeItemData.CNT_READ_AHEAD > ProjectTreeItemData.ROW_BUFFER_SIZE:
                self.__shrink_buffer__(going_up, item)

            if going_up:
                log.debug("going up")
                offset = item - ProjectTreeItemData.CNT_READ_AHEAD + 1
            else:
                offset = item

            for index, new_row in enumerate(self.project.get_next(offset,
                ProjectTreeItemData.CNT_READ_AHEAD, self.where_clause)):

                #~ log.debug("new_row: %s" % new_row)
                self.rows[offset + index] = new_row[1:]

            log.debug("size of row buffer: %s" % len(self.rows))

        return self.rows[item][col]

    def __shrink_buffer__(self, going_up, item):
        log.debug("shrinking buffer")
        new_buffer = {}
        for key, value in self.rows.iteritems():
            if going_up and key <= item + ProjectTreeItemData.ROW_BUFFER_SIZE:
                new_buffer[key] = value
            elif not going_up and key >= item - ProjectTreeItemData.ROW_BUFFER_SIZE:
                new_buffer[key] = value

        self.rows = new_buffer
        log.debug("buffer: %s, len: %s" % (sorted(self.rows.keys()), len(self.rows)))


    def IncomingMessage(self, msg):
        item_index = self.list_view.GetItemCount()
        self.__row_cnt__ += 1
        self.app_frame.sb.SetStatus('row_cnt', "Rows: %s" % self.__row_cnt__, True)
        log_repeat.debug("self.__row_cnt__: %s" % self.__row_cnt__)

        if len(self.rows) + 1 > ProjectTreeItemData.ROW_BUFFER_SIZE:
            self.__shrink_buffer__(False, item_index + ProjectTreeItemData.CNT_READ_AHEAD)
        log_repeat.debug("appending %s to list at %s" % (str(msg), item_index))
        self.rows[item_index] = msg
        self.list_view.SetItemCount(item_index + 1)
        #~ self.list_view.Refresh()
        if self.app_frame.auto_scroll:
            self.list_view.MoveLast()
        log_repeat.debug("IncomingMessage,size of row buffer: %s" % len(self.rows))


    def MarkAsUnRead(self):
        log.debug("MarkAsUnRead(%s)" % self.name)
        self.unread_count += 1
        self.tree.SetItemText(self.tree_node,
            "%s (%s)" % (self.name, self.unread_count))
        self.tree.SetItemBold(self.tree_node, True)

    def MarkAsRead(self):
        self.unread_count = 0
        self.tree.SetItemText(self.tree_node, self.name)
        self.tree.SetItemBold(self.tree_node, False)

class FilterTreeItemData(ProjectTreeItemData):
    def __init__(self, project, filter, list_view, app_frame, tree_node):
        ProjectTreeItemData.__init__(self, project, list_view, app_frame, tree_node)
        self.name = filter.name
        self.filter = filter
        self.filter_expression = filter.filter_expression
        self.where_clause = self.filter_expression.get_where(project.log_entries_table)


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


class MyFrame(wx.Frame):
    WINDOW_XML_FILENAME = 'var/window.xml'
    MAX_LIST_ITEMS = 100

    def __init__(
            self, parent, ID=wx.ID_ANY, title="Map the Internet",
            pos=wx.DefaultPosition,
            size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE
            ):

        wx.Frame.__init__(self, parent, ID, title, pos, size, style)

        col_width_dict = {}
        ctxt = None
        if os.path.exists(MyFrame.WINDOW_XML_FILENAME):
            doc = libxml2.parseFile(MyFrame.WINDOW_XML_FILENAME)
            root = doc.firstElementChild()
            left = root.prop('left')
            top = root.prop('top')
            self.SetPosition((int(left), int(top)))

            width = root.prop('width')
            height = root.prop('height')
            self.SetSize((int(width), int(height)))

            ctxt = doc.xpathNewContext()
            for item in ctxt.xpathEval("/window/col"):
                log.debug(str(item))
                col_name = item.prop('name')
                col_width = item.prop('width')
                col_width_dict[col_name] = int(col_width)

        self.splitter = wx.SplitterWindow(self)

        menuBar = wx.MenuBar()
        menuItem = wx.Menu()
        menuChild = menuItem.Append(wx.ID_ANY, "&New")
        self.Bind(wx.EVT_MENU, self.MenuNewProject, id=menuChild.GetId())
        menuBar.Append(menuItem, "&Project")

        menuItem = wx.Menu()

        menuChild = menuItem.Append(wx.ID_ANY, "&Mark all as read")
        self.Bind(wx.EVT_MENU, self.MenuMarkAllAsRead, id=menuChild.GetId())

        menuChild = menuItem.Append(wx.ID_ANY, "&Yield")
        self.Bind(wx.EVT_MENU, wx.YieldIfNeeded, id=menuChild.GetId())
        menuBar.Append(menuItem, "&Messages")

        self.SetMenuBar(menuBar)

        self.tree = wx.TreeCtrl(self.splitter, wx.ID_ANY, wx.DefaultPosition,
                           wx.DefaultSize, wx.TR_DEFAULT_STYLE)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.TreeOnSelChanged, self.tree)

        panel = wx.Panel(self.splitter)

        self.filter_textbox = wx.TextCtrl(panel, wx.ID_ANY, "Test it out and see")
        self.Bind(wx.EVT_TEXT, self.OnFilterBoxText)

        self.list_view = LogLinesListCtrlPanel(panel, col_width_dict)
        self.list_view.Bind(LogLinesListCtrlPanel.EVT_AT_BOTTOM, self.OnListViewAtBottom)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.filter_textbox, 0, wx.EXPAND)
        sizer.Add(self.list_view, 1, wx.EXPAND)
        panel.SetSizer(sizer)

        self.splitter.SetMinimumPaneSize(20)
        self.splitter.SplitVertically(self.tree, panel, 240)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_CLOSE, self.OnFormClose)

        self.sb = CustomStatusBar(self)
        self.SetStatusBar(self.sb)
        self.sb.SetStatus('message', 'Hi')
        self.SetAutoScroll(True)


        self.tree.Bind(EVT_LINE_READ, self.OnUpdate)
        self.projects = {}
        root = self.tree.AddRoot("LogViewer")

        self.tree_data = []
        self.LoadProject('logcat.logproj', ctxt)
        self.LoadProject('moblock.logproj', ctxt)
        log.debug("self.tree_data: %s" % len(self.tree_data))

    def OnSize(self, event):
        w,h = self.GetClientSizeTuple()
        self.splitter.SetDimensions(0, 0, w, h - 1)

    def OnFilterBoxText(self, event):
        text = event.GetString().strip()
        log.debug("text: %s" % text)
        try:
            expr = get_filter_class(text)
            log.debug("expr: %s" % expr)

            node_data = self.tree.GetPyData(self.tree.GetSelection())
            if node_data:
                log.debug("setting expr: %s" % expr)
                node_data.filter_expression = expr

        except ParsingFailedError:
            log.debug("ParsingFailedError")


    def MenuMarkAllAsRead(self, event):
        for item in self.tree_data:
            item.MarkAsRead()

    def YieldIfNeeded(self, event):
        wx.YieldIfNeeded()

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

        for item in self.projects.values():
            log.info("stopping thread %s" % str(item.uuid))
            item.reader.stop()

        for item in self.projects.values():
            log.info("wait for thread %s" % str(item.uuid))
            item.reader.join()

            #~ log.debug("project: %s" % item.uuid)
            #~ xml_project = root.newChild(None, 'project', None)
            #~ xml_project.setProp('uuid', str(item.uuid))
            #~ xml_project.setProp('pos', str(item.reader.pos))

        self.list_view.SaveColumnWidthDict()
        for key, value in self.list_view.GetColumnWidthDict().iteritems():
            log.debug("key: %s" % key)
            xml_col = root.newChild(None, 'col', None)
            xml_col.setProp('name', key)
            xml_col.setProp('width', str(value))

        log.debug("XML: %s" % doc.serialize())
        doc.saveFormatFile(MyFrame.WINDOW_XML_FILENAME, True)

        event.Skip()

    def MenuNewProject(self, event):
        pass

    def LoadProject(self, filename, ctxt):
        project = ReadFileProject(self.tree, ctxt, xml_filename=filename)
        self.projects[project.get_id()] = project

        if self.tree.GetChildrenCount(self.tree.GetRootItem()) == 1:
            self.tree.Expand(self.tree.GetRootItem())

        node_data = ProjectTreeItemData(project, self.list_view, self, project.root)
        self.tree.SetPyData(project.root, node_data)
        self.tree_data.append(node_data)

        for item in project.filters:
            node = self.tree.AppendItem(project.root, item.name)
            node_data = FilterTreeItemData(project, item, self.list_view, self, node)
            log.debug("node_data: %s" % node_data)
            self.tree.SetPyData(node, node_data)
            self.tree_data.append(node_data)

        self.tree.Expand(project.root)

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
        log_repeat.debug("got line: %s" % event.line)
        node = self.tree.GetSelection()
        node_data = self.tree.GetPyData(self.tree.GetSelection())
        #~ log_repeat.debug("type of node_data: %s" % type(node_data))

        for project in self.projects.values():
            match = project.line_filter.match(event.line.strip())
            if match:
                param_values = match.groups()
                db_rowid = project.append(param_values)
                #~ log_repeat.debug("db_rowid: %s" % db_rowid)

                values_with_rowid = [db_rowid]
                values_with_rowid.extend(param_values)

                for item_data in self.tree_data:
                    log.debug("project name: %s" % item_data.name)
                    if item_data.project.get_id() == project.get_id() and\
                        item_data.tree_node != node:

                        if item_data.filter_expression.eval_values(project.to_dict(values_with_rowid)):
                            log.debug("Hell yeah: %s" % item_data.name)
                            item_data.MarkAsUnRead()


                if node_data and node_data.project_id == project.get_id():
                    if node_data and node_data.filter_expression and\
                       node_data.filter_expression.eval_values(project.to_dict(values_with_rowid)):

                        node_data.IncomingMessage(values_with_rowid)

                        log_repeat.debug("add line: %s" % str(values_with_rowid))

                        #try:
                            ##~ pos = self.list_view.Append(param_values)
                            ##~ self.list_view.EnsureVisible(pos)
                            #log.debug("add line (dict): %s" % str(project.to_dict(values_with_rowid)))
                            #pass
                        #except UnicodeDecodeError:
                            #log.error("UnicodeDecodeError in TreeOnSelChanged()")


                #~ for filter_item in project.filters:
                    #~ if filter_item.filter_expression.eval_values(project.to_dict(param_values)):
                        #~ log.debug("[%s] filtered line: %s" % (filter_item.name, event.line))
                        #~ pass

                ##~ log.debug(match.groups())
                #logger_name = param_values[project.group_by]
                #if not logger_name in project.logger_infos:
                    ##~ log.debug("New logger_name: %s" % logger_name)
                    #child = self.tree.AppendItem(project.root, logger_name)
                    #loginfo = LoggerInfo(logger_name, child, self.tree, project.parameters)
                    ##~ self.tree.SetPyData(child, loginfo)
                    #self.tree.SetPyData(child, LoggerInfoItemData(loginfo, self.list_view))
                    #project.logger_infos[logger_name] = loginfo
                    #if self.tree.GetChildrenCount(project.root) == 1:
                        #self.tree.Expand(project.root)

                #loginfo = project.logger_infos[logger_name]
                #loginfo.messages.append(param_values)

                ##~ focused_loginfo = self.tree.GetPyData(self.tree.GetSelection())
                ##~ if focused_loginfo and focused_loginfo.name == logger_name:
                    ##~ log.debug("Focused!")
                    ##~ try:
                        ##~ pos = self.list_view.Append(param_values)
                        ##~ self.list_view.EnsureVisible(pos)
                    ##~ except UnicodeDecodeError:
                        ##~ log.error("UnicodeDecodeError in TreeOnSelChanged()")
                ##~ else:
                    ##~ loginfo.MarkAsUnRead()

                return

        log_repeat.warn("failed match '%s'" % event.line)

    def SetAutoScroll(self, value):
        if value:
            self.sb.SetStatus('scroll_lock', 'Auto Scroll')
        else:
            self.sb.SetStatus('scroll_lock', '')
        self.auto_scroll = value

    def OnListViewAtBottom(self, event):
        log.debug("OnListViewAtBottom(%s)" % event.value)
        self.SetAutoScroll(event.value)



def main():
    app = wx.App()
    win = MyFrame(None, pos=(0,0), size=(1024, 800))
    win.Show()

    log.info("entering main loop")
    app.MainLoop()

if __name__ == '__main__':
    main()
