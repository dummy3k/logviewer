import logging
from simpleparse import generator
from mx.TextTools import TextTools
from pprint import pprint

log = logging.getLogger(__name__)

decl =\
"""
whitespace      := [ \\t\\r\\n]+
alphanums       := [a-zA-Z0-9]+
wordpunct       := [-_]
word            := alphanums, (wordpunct, alphanums)*
equal           := word, ' '*, '=', ' '*, quoted
quote           := ['"]
quoted          := quote, (word / whitespace)+, quote
<binary_op>     := (equal / in_expr)
and_expr        := binary_op, (' and ', binary_op)+
#~ boolean_values  := ('True' / 'False')
in_expr         := word, ' in (', quoted, (', ', quoted)* , ')'
expression      := (and_expr / binary_op)
"""

def check_parse(parser, input, show_ast=False):
    """
        >>> check_parse('equal', 'no match')
        Traceback (most recent call last):
        Exception: unmatched sequence: "match"

        >>> check_parse('quoted', "'Hello World'")
        True

        >>> check_parse('equal', "lvl = 'x'")
        True

        >>> check_parse('and_expr', "lvl = 'x' and logger='vm' and foo='bar'")
        True

        >>> check_parse('in_expr', "x in ('x', 'xx')", False)
        True

        >>> check_parse('expression', "x in ('x', 'xx')", False)
        True

        x>>> check_parse('expression', "x in ('x', 'xx') and x='x'", False)
        True
    """
    parser = generator.buildParser(decl).parserbyname(parser)
    retval = TextTools.tag(input, parser)
    if show_ast:
        pprint(retval)
    if len(input) != retval[2]:
        raise Exception('unmatched sequence: "%s"' % ( input[retval[2]:]))
    return True


class ParsingFailedError(Exception):
    pass

def parse(parser_name, input):
    """
        execute parse and return result as if it was a sub group.

        This is what normally happens. Notice that the result does
        not contain 'quoted'
        >>> parser = generator.buildParser(decl).parserbyname('quoted')
        >>> input = "'foo'"
        >>> pprint(TextTools.tag(input, parser))
        (1,
         [('quote', 0, 1, None),
          ('word', 1, 4, [('alphanums', 1, 4, None)]),
          ('quote', 4, 5, None)],
         5)

        >>> pprint(parse('quoted', input))
        ['quoted',
         0,
         5,
         [('quote', 0, 1, None),
          ('word', 1, 4, [('alphanums', 1, 4, None)]),
          ('quote', 4, 5, None)]]

    """
    parser = generator.buildParser(decl).parserbyname(parser_name)
    tags = TextTools.tag(input, parser)
    if tags[0] == 0 or tags[2] != len(input):
        raise ParsingFailedError("parsing failed")

    return [parser_name, 0, tags[2], tags[1]]

class EqualExpression():
    def __init__(self, var_name, var_value):
        self.var_name = var_name
        self.var_value = var_value

    def __repr__(self):
        return "EqualExpression(%s, '%s')" % (self.var_name, self.var_value)

    def eval_values(self, values):
        """
            >>> expr = EqualExpression('foo', 'bar')
            >>> expr.eval_values({'foo':'bar'})
            True

            >>> expr.eval_values({'foo':'xyz'})
            False

            >>> expr.eval_values({'xyz':'bar'})
            Traceback (most recent call last):
            Exception: Variable not defiend: 'foo'

            >>> expr.eval_values({'abc':'xyz', 'foo':'bar'})
            True
        """
        try:
            return values[self.var_name] == self.var_value
        except KeyError:
            raise Exception("Variable not defiend: '%s'" % self.var_name)

    def get_where(self, table):
        """
            >>> from sqlalchemy import Table, Column, Integer, MetaData
            >>> t = Table('my_table', MetaData(), Column('id', Integer))
            >>> expr = EqualExpression('id', '7')
            >>> str(expr.get_where(t))
            "my_table.id = '7'"
        """
        from sqlalchemy import text
        return table.columns[self.var_name] == text("'%s'" % self.var_value)

class AndExpression():
    def __init__(self, condition1, condition2):
        self.condition1 = condition1
        self.condition2 = condition2

    def __repr__(self):
        return "AndExpression(%s, '%s')" % (self.condition1, self.condition2)

    def eval_values(self, values):
        """
            >>> equal_expr_1 = EqualExpression('foo', 'bar')
            >>> equal_expr_2 = EqualExpression('xyz', 'abc')
            >>> expr = AndExpression(equal_expr_1, equal_expr_2)
            >>> expr.eval_values({'foo':'bar', 'xyz':'abc'})
            True

            >>> expr.eval_values({'foo':'baz', 'xyz':'abc'})
            False

            >>> expr.eval_values({'foo':'bar', 'xyz':'abcd'})
            False
        """
        if not self.condition1.eval_values(values):
            return False
        return self.condition2.eval_values(values)

class InExpression():
    def __init__(self, var_name, var_values):
        self.var_name = var_name
        self.var_values = tuple(var_values)

    def __repr__(self):
        return "InExpression(%s, %s)" % (self.var_name, self.var_values)

    def eval_values(self, values):
        """
            >>> expr = InExpression('foo', ('foo', 'bar', 'baz'))
            >>> expr.eval_values({'foo':'bar'})
            True
            >>> expr.eval_values({'foo':'baz'})
            True
            >>> expr.eval_values({'foo':'xyz'})
            False
        """
        for item in self.var_values:
            if values[self.var_name] == item:
                return True
        return False

    def get_where(self, table):
        """
            >>> from sqlalchemy import Table, Column, Integer, MetaData
            >>> t = Table('my_table', MetaData(), Column('id', Integer))
            >>> expr = InExpression('id', ['7', '8', '9'])
            >>> stm = expr.get_where(t)
            >>> print(stm)
            my_table.id IN (:id_1, :id_2, :id_3)

            >>> print(stm.compile().params)
            {u'id_2': '8', u'id_3': '9', u'id_1': '7'}
        """
        return table.columns[self.var_name].in_(self.var_values)

class TrueExpression():
    def eval_values(self, values):
        return True

IDX_CHILDREN = 3
from simpleparse.dispatchprocessor import DispatchProcessor, getString, dispatchList
class ProcessessExpression(DispatchProcessor):
    def and_expr(self, tags, buffer):
        """
            >>> input = "foo = 'bar' and foo2 = 'bar2'"
            >>> proc = ProcessessExpression()
            >>> proc(parse('and_expr', input), input)
            AndExpression(EqualExpression(foo, 'bar'), 'EqualExpression(foo2, 'bar2')')
        """
        expr_1 = self(tags[IDX_CHILDREN][0], buffer)
        expr_2 = self(tags[IDX_CHILDREN][1], buffer)
        return AndExpression(expr_1, expr_2)

    def in_expr(self, tags, buffer):
        """
            >>> input = "foo in ('bar', 'baz', 'barbar')"
            >>> proc = ProcessessExpression()
            >>> proc(parse('in_expr', input), input)
            InExpression(foo, ('bar', 'baz', 'barbar'))
        """
        retval = result = dispatchList(self, tags[IDX_CHILDREN], buffer )
        #~ pprint(retval)
        return InExpression(retval[0], retval[1:])
        var_name = self(tags[IDX_CHILDREN][0], buffer)
        var_value = self(tags[IDX_CHILDREN][1], buffer)
        return EqualExpression(var_name, var_value)

    def equal(self, tags, buffer):
        """
            >>> proc = ProcessessExpression()
            >>> input = "foo = 'bar'"
            >>> proc(parse('equal', input), input)
            EqualExpression(foo, 'bar')

            >>> input = "logger_name = 'dalvikvm'"
            >>> proc(parse('equal', input), input)
            EqualExpression(logger_name, 'dalvikvm')
        """
        #~ pprint(tags)
        var_name = self(tags[IDX_CHILDREN][0], buffer)
        var_value = self(tags[IDX_CHILDREN][1], buffer)
        return EqualExpression(var_name, var_value)

    def quote(self, tag, buffer):
        return None

    def quoted(self, tags, buffer):
        """
            >>> proc = ProcessessExpression()
            >>> input = "'foo'"
            >>> proc(parse('quoted', input), input)
            'foo'
            >>> input = "'foo bar'"
            >>> proc(parse('quoted', input), input)
            'foo bar'
        """
        retval = result = dispatchList(self, tags[IDX_CHILDREN], buffer )
        def concat(values):
            retval = ''
            for item in values:
                if item:
                    retval += item
            return retval

        retval = concat(retval)
        #~ pprint(retval)
        return retval
        return self(tags[IDX_CHILDREN][1], buffer)

    def word(self, tags, buffer):
        """
            >>> proc = ProcessessExpression()
            >>> input = "foo"
            >>> proc(parse('word', input), input)
            'foo'

            >>> input = "logger_name"
            >>> proc(parse('word', input), input)
            'logger_name'
        """
        return buffer[int(tags[1]):int(tags[2])]
        return self(tags[IDX_CHILDREN][0], buffer)

    def alphanums(self, tags, buffer):
        """
            >>> input = "foo"
            >>> proc = ProcessessExpression()
            >>> proc(parse('alphanums', input), input)
            'foo'
        """
        return getString(tags, buffer)

    def whitespace(self, tags, buffer):
        return getString(tags, buffer)

    def expression(self, tags, buffer):
        """
            >>> input = "foo = 'bar' and foo2 = 'bar2'"
            >>> proc = ProcessessExpression()
            >>> proc(parse('expression', input), input)
            AndExpression(EqualExpression(foo, 'bar'), 'EqualExpression(foo2, 'bar2')')
        """
        log.debug("expression: %s" % str(tags))
        return self(tags[IDX_CHILDREN][0], buffer)

def get_filter_class(filter_expression_str):
    proc = ProcessessExpression()
    tags = parse('expression', filter_expression_str)
    return proc(tags, filter_expression_str)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

    #~ pprint(parse('equal', "lvl = 'x'"))
