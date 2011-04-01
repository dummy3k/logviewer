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
