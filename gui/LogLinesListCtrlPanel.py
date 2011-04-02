import logging
import wx
import wx.lib.mixins.listctrl  as  listmix

log = logging.getLogger(__name__)

class LogLinesListCtrlPanel(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    (AtBottomChangedEvent, EVT_AT_BOTTOM) = wx.lib.newevent.NewEvent()

    def __init__(self, parent, col_width_dict):
        wx.ListCtrl.__init__(self, parent, -1, style=wx.WANTS_CHARS | wx.LC_REPORT | wx.LC_VIRTUAL)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        #~ self.Bind(wx.EVT_LEFT_DOWN, self.OnPaint)
        self.OnGetItemTextCallback = None
        self.__last_top_item = None
        self.at_bottom = None
        self.__col_width__ = col_width_dict

    def SetColumns(self, col_names):
        log.debug("LogLinesListCtrlPanel.SetColumns")
        self.DeleteAllItems()
        self.DeleteAllColumns()
        for index, name in enumerate(col_names):
            self.InsertColumn(index, name)
            if name in self.__col_width__:
                self.SetColumnWidth(index, self.__col_width__[name])

    def MoveLast(self):
        log.debug("LogLinesListCtrlPanel.FitAndMoveLast")
        self.EnsureVisible(self.GetItemCount() - 1)

    #~ def FitAndMoveLast(self):
        #~ log.debug("LogLinesListCtrlPanel.FitAndMoveLast")
        #~ self.EnsureVisible(self.GetItemCount() - 1)
        #~ for index in range(self.GetColumnCount()):
            #~ self.SetColumnWidth(index, wx.LIST_AUTOSIZE)

    def OnGetItemText(self, item, col):
        #~ log.debug("LogLinesListCtrlPanel.OnGetItemText()")
        if not self.OnGetItemTextCallback:
            return "no self.OnGetItemTextCallback"
        return self.OnGetItemTextCallback.OnGetItemText(item, col)


    def OnPaint(self, event):
        #~ log.debug("OnPaint()")
        bottom = self.GetTopItem() + self.GetCountPerPage()
        #~ log.debug("bottom: %s, ItemCount: %s" % (bottom, self.GetItemCount()))
        new_value = (bottom == self.GetItemCount())

        if self.at_bottom != new_value:
            log.debug("at_bottom, changed: %s" % new_value)
            self.at_bottom = new_value
            evt = LogLinesListCtrlPanel.AtBottomChangedEvent(value=new_value)
            wx.PostEvent(self, evt)

        #~ log.debug("at_bottom: %s" % self.at_bottom)


    def SaveColumnWidthDict(self):
        #~ retval = {}
        for index in range(self.GetColumnCount()):
            col_name = self.GetColumn(index).GetText()
            self.__col_width__[col_name] = self.GetColumnWidth(index)
        #~ return retval

    def GetColumnWidthDict(self):
        return self.__col_width__

    def SaveLayout(self, xml_parent):
        root = xml_parent.newChild(None, 'LogLinesListCtrlPanel', None)
        for index in range(self.GetColumnCount()):
            xml_col = root.newChild(None, 'col', None)
            xml_col.setProp('width', str(self.GetColumnWidth(index)))
            #~ log.debug("col: %s" % )

            col_name = self.GetColumn(index).GetText()
            xml_col.setProp('name', col_name)

