import logging
import wx
log = logging.getLogger(__name__)

class CustomStatusBar(wx.StatusBar):
    def __init__(self, parent):
        wx.StatusBar.__init__(self, parent, wx.ID_ANY)

        self.labels = {'message':-1, 'row_cnt':10, 'scroll_lock':80}
        self.SetFieldsCount(len(self.labels))
        self.SetStatusWidths(self.labels.values())

    def SetStatus(self, label, value, auto_size=False):
        idx = self.labels.keys().index(label)
        self.SetStatusText(str(value), idx)
        if auto_size:
            w, h = self.GetTextExtent(str(value))
            self.labels[label] = w
            self.SetStatusWidths(self.labels.values())

