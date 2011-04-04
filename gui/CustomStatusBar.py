import logging
import wx
log = logging.getLogger(__name__)

class CustomStatusBar(wx.StatusBar):
    def __init__(self, parent):
        wx.StatusBar.__init__(self, parent, wx.ID_ANY)


        #~ self.labels = {'message':-1, 'project':10, 'filter_name':10,
                       #~ 'row_cnt':10, 'scroll_lock':80}

        definition  = [['message',-1],
                       ['project',10],
                       ['filter_name',10],
                       ['row_cnt',10],
                       ['scroll_lock',80]]
        self.labels = map(lambda x: x[0], definition)
        self.width = map(lambda x: x[1], definition)


        self.SetFieldsCount(len(self.labels))
        self.SetStatusWidths(self.width)

    def SetStatus(self, label, value, auto_size=False):
        idx = self.labels.index(label)
        self.SetStatusText(str(value), idx)
        if auto_size:
            w, h = self.GetTextExtent(str(value))
            self.width[idx] = w + 10
            self.SetStatusWidths(self.width)

