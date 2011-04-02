import wx

class CustomStatusBar(wx.StatusBar):
    def __init__(self, parent):
        wx.StatusBar.__init__(self, parent, wx.ID_ANY)

        self.labels = {'message':-1, 'scroll_lock':80}
        # This status bar has three fields
        self.SetFieldsCount(len(self.labels))
        # Sets the three fields to be relative widths to each other.
        self.SetStatusWidths(self.labels.values())

    def SetStatus(self, label, value):
        idx = self.labels.keys().index(label)
        self.SetStatusText(value, idx)

