import logging
import re, os
import libxml2

if __name__ == '__main__':
    import logging.config
    #~ logging.basicConfig()
    logging.config.fileConfig("logging.conf")
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy import select


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
            self.sqlite_url = readFileNode.prop('sqliteUrl')

            pnodes = ctxt.xpathEval("/readFile/lineFilter/parameter")
            self.parameters = map(lambda x: x.prop('name'), pnodes)
            log.debug("self.parameters: %s" % self.parameters)

            lineFilterNode = ctxt.xpathEval("/readFile/lineFilter")[0]
            regex_str = lineFilterNode.prop('regex')
            self.line_filter = re.compile(regex_str)
            self.group_by = int(lineFilterNode.prop('groupBy'))
        else:
            raise TypeError('bad arguments')

        self.create_database()

        if self.tree:
            self.root = self.tree.AppendItem(self.tree.GetRootItem(),
                                             os.path.basename(filename))
            #~ self.tree.SetPyData(self.root, self)
            self.reader = FileReader(filename, self.tree)
            self.reader.Start()

    def create_database(self):
        engine = create_engine(self.sqlite_url)
        metadata = MetaData()
        self.log_entries_table = Table('log_entries', metadata,
            Column('id', Integer, primary_key=True)
        )
        for item in self.parameters:
            col = Column(item, String)
            self.log_entries_table.append_column(col)

        metadata.create_all(engine)

    def get_id(self):
        return self.reader.thread_id

    def save_to_file(self, filename):
        pass

    def append(self, values):
        engine = create_engine(self.sqlite_url)
        val_map = {}
        for index, key in enumerate(self.parameters):
            val_map[key] = values[index]

        engine.execute(self.log_entries_table.insert(), val_map)

    def get_last(self, count):
        query = select([self.log_entries_table]).\
                order_by(self.log_entries_table.c.id.desc()).\
                limit(count)
        engine = create_engine(self.sqlite_url)
        result = engine.execute(query).fetchall()
        result.reverse()
        return result

if __name__ == '__main__':
    log.info("Start")
    project = ReadFileProject(None, xml_filename='logcat.logproj')
    #~ logging.getLogger('sqlalchemy.engine').info("hi")
    #~ project.create_database('sqlite:///:memory:')
    project.create_database()
    project.append(('level', 'name', 't', 'message3'))
    project.append(('level', 'name', 't', 'message2'))
    for item in project.get_last(3):
        print(str(item))

