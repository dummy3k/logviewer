import logging
import re, os
import libxml2
from read_file_thread import FileReader, EVT_LINE_READ

log = logging.getLogger(__name__)

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

