import logging
import re, os
import libxml2
import uuid

if __name__ == '__main__':
    import logging.config
    #~ logging.basicConfig()
    logging.config.fileConfig("logging.conf")
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy import select, func

from read_file_thread import EVT_LINE_READ, create_process
from filter import get_filter_class

log = logging.getLogger(__name__)

class ReadFileProject():
    def __init__(self, *args, **kwargs):
        self.logger_infos = {}
        self.tree = args[0]
        tmp_xml_root = args[1]

        if 'log_file_name' in kwargs:
            pass
        elif 'xml_filename' in kwargs:
            doc = libxml2.parseFile(kwargs['xml_filename'])
            ctxt = doc.xpathNewContext()
            readFileNode = ctxt.xpathEval("/readFile")[0]
            filename = readFileNode.prop('filename')
            self.sqlite_url = readFileNode.prop('sqliteUrl')
            self.uuid = uuid.UUID(readFileNode.prop('uuid'))

            pnodes = ctxt.xpathEval("/readFile/lineFilter/parameter")
            self.parameters = map(lambda x: x.prop('name'), pnodes)
            self.parameters.insert(0, "rowid")
            log.debug("self.parameters: %s" % self.parameters)

            lineFilterNode = ctxt.xpathEval("/readFile/lineFilter")[0]
            regex_str = lineFilterNode.prop('regex')
            self.line_filter = re.compile(regex_str)
            self.group_by = int(lineFilterNode.prop('groupBy'))

            self.filters = map(lambda x: FilterNode(x), ctxt.xpathEval("/readFile/filter"))

            pos_node = tmp_xml_root.xpathEval("/window/project[@uuid='%s']" % str(self.uuid))[0]
            start_pos = int(pos_node.prop('pos'))
            log.debug("start_pos: %s" % start_pos)

        else:
            raise TypeError('bad arguments')

        self.create_database()

        if self.tree:
            log.debug("launching thread")
            self.root = self.tree.AppendItem(self.tree.GetRootItem(),
                                             os.path.basename(filename))
            #~ self.tree.SetPyData(self.root, self)
            self.reader, self.reader_pos = create_process(filename, self.tree, start_pos)
            self.reader.start()

    def get_name():
        pass

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
        return self.reader.ident

    def save_to_file(self, filename):
        pass

    def append(self, values):
        engine = create_engine(self.sqlite_url)
        val_map = self.to_dict(values, False)
        engine.execute(self.log_entries_table.insert(), val_map)
        return -1

    def get_last(self, count, where_expr=None):
        raise Exception("unused?")

        query = select([self.log_entries_table])
        if where_expr:
            query = query.where(where_expr.where())

        query = query.\
                order_by(self.log_entries_table.c.id.desc()).\
                limit(count)
        engine = create_engine(self.sqlite_url)
        result = engine.execute(query).fetchall()
        result.reverse()
        return result

    def get_row_count(self, whereclause):
        query = select([func.count("*")], from_obj=[self.log_entries_table], whereclause=whereclause)
        log.debug("get_row_count:\n%s" % str(query))
        engine = create_engine(self.sqlite_url)
        result = engine.execute(query).fetchall()
        return result[0][0]

    def get_next(self, offset, count, where_expr=None):
        #~ query = select([self.log_entries_table]).\
                #~ offset(offset).\
                #~ limit(count)

        log.debug("get_next, where_expr: %s" % str(where_expr))
        query = select([self.log_entries_table], whereclause=where_expr)
        #~ if where_expr != None:
            #~ query = query.where(where_expr)

        query = query.\
                offset(offset).\
                limit(count)

        log.debug("SQL:\n%s" % str(query))
        engine = create_engine(self.sqlite_url)
        result = engine.execute(query).fetchall()
        return result

    def to_dict(self, values, with_rowid=True):
        val_map = {}
        if with_rowid:
            for index, key in enumerate(self.parameters):
                    val_map[key] = values[index]
        else:
            for index, key in enumerate(self.parameters):
                if key != "rowid":
                    val_map[key] = values[index - 1]

        return val_map

class FilterNode():
    def __init__(self, filterNode):
        #~ proc = ProcessessExpression()
        filter_expression_str = filterNode.content.strip()
        #~ self.filter_expression = proc(parse_filter('expression', filter_expression_str), filter_expression_str)
        self.filter_expression = get_filter_class(filter_expression_str)
        self.name = filterNode.prop('name')

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


