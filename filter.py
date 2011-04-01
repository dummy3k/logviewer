from simpleparse import generator
from mx.TextTools import TextTools
from pprint import pprint

decl =\
"""
para           := (plain / markup)+
plain          := (word / whitespace / punctuation)+
whitespace     := [ \t\r\n]+
alphanums      := [a-zA-Z0-9]+
word           := alphanums, (wordpunct, alphanums)*, contraction?
wordpunct      := [-_]
contraction    := "'", ('am'/'clock'/'d'/'ll'/'m'/'re'/'s'/'t'/'ve')
markup         := emph / strong / module / code / title
emph           := '-', plain, '-'
strong         := '*', plain, '*'
module         := '[', plain, ']'
code           := "'", plain, "'"
title          := '_', plain, '_'
punctuation    := (safepunct / mdash)
mdash          := '--'
safepunct      := [!@#$%^&()+=|\{}:;<>,.?/"]
"""

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

def get_word(s, tags):
    #~ print(parser_group)
    return s[tags[1]:tags[2]]

def test_equal(condition, var_values):
    """
        >>> test_equal("lvl = 'x'", {'lvl':'x'})
        True
        >>> test_equal("lvl = 'abc'", {'lvl':'x'})
        False
        >>> test_equal("lvl='x'", {'lvl':'x'})
        True
    """
    return test_eval(condition, var_values, 'equal', eval_equal)

def test_eval(condition, var_values, parse_name, fn):
    """
        >>> test_eval("lvl = 'x'", {'lvl':'x'}, 'equal', eval_equal)
        True
    """
    parser = generator.buildParser(decl).parserbyname(parse_name)
    tags = TextTools.tag(condition, parser)
    if len(condition) != tags[2]:
        raise Exception('unmatched sequence: "%s"' % ( condition[tags[2]:]))
    return fn(condition, tags[1], var_values)

def eval_equal(condition, tags, var_values):
    #~ pprint(tags)
    key = get_word(condition, tags[0])
    value = get_word(condition, tags[1][3][1])
    return (var_values[key] == value)

def get_quoted(expression_str, tags):
    return get_word(expression_str, tags[3][1])

def test_and(expression_str):
    """
        >>> stm = test_and("x='x' and y='y'")
        >>> stm({'x':'x', 'y':'y'})
        True

        >>> stm = test_and("x='x' and y='a'")
        >>> stm({'x':'x', 'y':'y'})
        False
        >>> stm({'x':'x', 'y':'a'})
        True

        >>> stm = test_and("x='x' and y='y' and a='a'")
        >>> stm({'x':'x', 'y':'y', 'a':'b'})
        False
    """
    return lambda x: test_eval(expression_str, x, 'and_expr', eval_and)

def eval_and(condition, tags, var_values):
    #~ pprint(tags)
    for item in tags:
        if not eval_equal(condition, item[3], var_values):
            return False

    return True

def test_in(expression_str):
    """
        >>> stm = test_in("x in ('x', 'xx')")
        >>> stm({'x':'x', 'y':'y'})
        True

        >>> stm = test_in("x in ('ax', 'xx')")
        >>> stm({'x':'x', 'y':'y'})
        False
    """
    #~ return lambda x: True
    return lambda x: test_eval(expression_str, x, 'in_expr', eval_in)

def eval_in(expression_str, tags, var_values):


    #~ pprint(tags)

    #(1,
     #[('word', 0, 1, [('alphanums', 0, 1, None)]),
      #('quoted',
       #6,
       #9,
       #[('quote', 6, 7, None),
        #('word', 7, 8, [('alphanums', 7, 8, None)]),
        #('quote', 8, 9, None)]),
      #('quoted',
       #11,
       #15,
       #[('quote', 11, 12, None),
        #('word', 12, 14, [('alphanums', 12, 14, None)]),
        #('quote', 14, 15, None)])],
     #16)

    left_var_name = get_word(expression_str, tags[0])
    #~ value = var_values[
    for item in tags[1:]:
        right_var_value = get_quoted(expression_str, item)  #get_word(expression_str, item[3][1])
        if var_values[left_var_name] == right_var_value:
            return True

    return False

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
    return [parser_name, 0, tags[2], tags[1]]

class EqualExpression():
    def __init__(self, var_name, var_value):
        self.var_name = var_name
        self.var_value = var_value

    def __repr__(self):
        return "EqualExpression(%s, '%s')" % (self.var_name, self.var_value)

class AndExpression():
    def __init__(self, condition1, condition2):
        self.condition1 = condition1
        self.condition2 = condition2

    def __repr__(self):
        return "AndExpression(%s, '%s')" % (self.condition1, self.condition2)

class InExpression():
    def __init__(self, var_name, var_values):
        self.var_name = var_name
        self.var_values = tuple(var_values)

    def __repr__(self):
        return "InExpression(%s, %s)" % (self.var_name, self.var_values)

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
            >>> input = "foo = 'bar'"
            >>> proc = ProcessessExpression()
            >>> proc(parse('equal', input), input)
            EqualExpression(foo, 'bar')
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
            >>> input = "foo"
            >>> proc = ProcessessExpression()
            >>> proc(parse('word', input), input)
            'foo'
        """
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


if __name__ == '__main__':
    import doctest
    doctest.testmod()

    #~ pprint(parse('equal', "lvl = 'x'"))
