import inspect
from contextlib import suppress
from src.AST.Operators import Operators
import pyparsing as pp
from pyparsing import pyparsing_common as ppc
from src.AST.Nodes import *
import re

class Parser:
    """ Класс, который используется для парсинга кода. """
    def __init__(self):
        self.grammar = self.__mk_grammar()
        self._locs = []

    def __mk_grammar(self):
        """ Метод, в котором создаётся описание грамматики, вызывается в конструкторе класса Parser. """
        # Описание LiteralNode и IdentNode
        num = ppc.integer() | ppc.real()
        str_ = pp.QuotedString('"', escChar='\\', unquoteResults=True, convertWhitespaceEscapes=False)
        literal = (num | str_).setName('Literal')
        ident = ppc.identifier.setName('Ident')
        # Описание ключевых слов
        VAR_KW, FUNC_KW, RETURN_KW = pp.Keyword('var'), pp.Keyword('def'), pp.Keyword('return')
        IF_KW, ELSE_KW = pp.Keyword('if'), pp.Keyword('else')
        FOR_KW, DO_KW, WHILE_KW = pp.Keyword('for'), pp.Keyword('do'), pp.Keyword('while')
        # Описание различных скобок, запятой и точки с запятой.
        L_PAR, R_PAR = pp.Literal('(').suppress(), pp.Literal(')').suppress()
        L_BRACKET, R_BRACKET = pp.Literal('{').suppress(), pp.Literal('}').suppress()
        SEMICOLON, COMMA, COLON = pp.Literal(';').suppress(), pp.Literal(',').suppress(), pp.Literal(':').suppress()
        # Описание операторов
        ASSIGN = pp.Literal('=')
        ADD, SUB, MUL, DIV, MOD, EXP = pp.Literal('+'), pp.Literal('-'), pp.Literal('*'), pp.Literal('/'), \
                                       pp.Literal('%'), pp.Literal('**')
        LOG_AND, LOG_OR, LOG_NOT = pp.Literal('&&'), pp.Literal('||'), pp.Literal('!')
        GT, LT, GE, LE = pp.Literal('>'), pp.Literal('<'), pp.Literal('>='), pp.Literal('<=')
        NEQ, EQ = pp.Literal('!='), pp.Literal('==')
        INCR, DECR = pp.Literal('++'), pp.Literal('--')

        # Объявляем переменные, описывающие операции умножения, сложения и Выражение. Они определяются дальше в коде.
        mul_op = pp.Forward()
        add_op = pp.Forward()
        expr = pp.Forward()
        # Описание вызова функции
        call = (ident + L_PAR + pp.Optional(expr + pp.ZeroOrMore(COMMA + expr)) + R_PAR).setName('Call')
        # Описание унарных операций: инкремент, декремент.
        incr_op = (ident + INCR).setName('UnaryExpr')
        decr_op = (ident + DECR).setName('UnaryExpr')

        group = (literal | call | ident | L_PAR + expr + R_PAR)

        # Описание бинарных выражений.
        mul_op << pp.Group(group + pp.ZeroOrMore((EXP | MUL | DIV | MOD) + group)).setName('BinExpr')
        add_op << pp.Group(mul_op + pp.ZeroOrMore((ADD | SUB) + mul_op)).setName('BinExpr')
        compare = pp.Group(add_op + pp.ZeroOrMore((GE | LE | GT | LT) + add_op)).setName('BinExpr')
        compare_eq = pp.Group(compare + pp.ZeroOrMore((EQ | NEQ) + compare)).setName('BinExpr')
        log_and_op = pp.Group(compare_eq + pp.ZeroOrMore(LOG_AND + compare_eq)).setName('BinExpr')
        log_or_op = pp.Group(log_and_op + pp.ZeroOrMore(LOG_OR + log_and_op)).setName('BinExpr')
        expr << log_or_op

        # Описание присвоения и объявления переменных.
        assign = (ident + ASSIGN + expr).setName('BinExpr')
        simple_assign = (ident + ASSIGN.suppress() + expr)
        var_item = simple_assign | ident
        simple_var = (VAR_KW.suppress() + var_item).setName('Declarator')
        mult_var_item = (COMMA + var_item).setName('Declarator')
        mult_var = (simple_var + pp.ZeroOrMore(mult_var_item)).setName('VarDeclaration')

        stmt = pp.Forward()
        simple_stmt = assign | call | incr_op | decr_op

        # Описание цикла for.
        for_statement_list = pp.Optional(simple_stmt + pp.ZeroOrMore(COMMA + simple_stmt)).setName('BlockStatement')
        for_statement = simple_var | for_statement_list
        for_test = expr | pp.Group(pp.empty)
        for_block = stmt | pp.Group(SEMICOLON).setName('BlockStatement')

        # Описание циклов for, while, условного оператора if.
        if_ = (IF_KW.suppress() + expr + stmt + pp.Optional(ELSE_KW.suppress() + stmt)).setName('If')
        for_ = (FOR_KW.suppress() + L_PAR + for_statement + SEMICOLON + for_test + SEMICOLON +
                for_statement + R_PAR + for_block).setName('For')
        while_ = (WHILE_KW.suppress() + expr + stmt).setName('While')
        # Описание блока кода, аргументов функции, объявления функции и оператора return.
        block = pp.ZeroOrMore(stmt).setName('BlockStatement')
        br_block = COLON + block + R_BRACKET
        args = ((expr + pp.ZeroOrMore(COMMA + expr)) | pp.Group(pp.empty)).setName("Args")
        func_decl = (FUNC_KW.suppress() + ident + L_PAR + args + R_PAR + br_block)\
            .setName('FuncDeclaration')
        return_ = (RETURN_KW.suppress() + expr).setName('Return')

        stmt << (
                if_ |
                for_ |
                while_ |
                br_block |
                simple_stmt |
                func_decl |
                return_
        )

        # locals().copy().items() возвращает словарь всех переменных в текущей области видимости
        # все элементы этого словаря перебираются в цикле for
        for var_name, value in locals().copy().items():
            # проверка на то, что текущий элемент является экземлпяром класса ParserElement
            if isinstance(value, pp.ParserElement):
                # вызов метода __set_parse_action
                self.__set_parse_action(var_name, value)

        return block.ignore(pp.pythonStyleComment) + pp.stringEnd

    def __set_parse_action(self, rule_name: str, rule: pp.ParserElement):
        """ Этот метод задаёт то, какой конструктор вызывается при успешном распознавании правила грамматики. """
        # если rule_name написан КАПСОМ, то никаких действий совершать не нужно,
        # потому что КАПСОМ мы обозначили названия переменных, в которых описываются различные операторы.
        if rule_name == rule_name.upper():
            return
        # Каждому правилу присваивется название соответствующего класса, если оно было задано методом setName().
        if getattr(rule, 'name', None) and rule.name.isidentifier():
            rule_name = rule.name
        # Если имя правила — "BinExpr", то определяется метод, который будет разбирать бинарное выражение.
        if rule_name in ('BinExpr', ):
            # Этот метод вернёт экземпляр класса BinExprNode.
            def bin_op_parse_action(s, loc, toks):
                # toks - список распознанных элементов
                node = toks[0]
                if not isinstance(node, TreeNode):
                    node = bin_op_parse_action(s, loc, node)
                for i in range(1, len(toks) - 1, 2):
                    secondNode = toks[i + 1]
                    if not isinstance(secondNode, TreeNode):
                        secondNode = bin_op_parse_action(s, loc, secondNode)
                    # Когда распознана правая часть, создаётся экземпляр класса BinExprNode.
                    node = BinExprNode(self._locs[loc][0], self._locs[loc][1],
                                       Operators(toks[i]), node, secondNode)
                return node
            # Задаётся действие при успешном распознавании текущего правила - вызов функции bin_op_parse_action.
            rule.setParseAction(bin_op_parse_action)
        # Если имя правила — "UnaryExpr", то определяется метод, который будет разбирать унарное выражение.
        elif rule_name in ('UnaryExpr', ):
            # Этот метод вернёт экземпляр класса UnaryExprNode.
            def un_op_parse_action(s, loc, toks):
                # toks - список распознанных элементов
                node = toks[0]
                if not isinstance(node, TreeNode):
                    node = un_op_parse_action(s, loc, node)
                for i in range(1, len(toks)):
                    # Создаётся экземпляр класса UnaryExprNode.
                    node = UnaryExprNode(self._locs[loc][0], self._locs[loc][1], Operators(toks[i]), node)
                return node
            # Задаётся действие при успешном распознавании текущего правила - вызов функции un_op_parse_action.
            rule.setParseAction(un_op_parse_action)
        # В случае, когда не выполнилось ни одно из предшествующих условий, выполняется следующий фрагмент кода:
        else:
            # cls хранит название класса в виде: название_правила + Node,
            # это соответствует названию классов в фалйе Nodes.py.
            cls = rule_name + 'Node'
            # Во избежание вызова исключения NameError используется конструкция with suppress(NameError):
            with suppress(NameError):
                # Теперь в переменой cls хранится тип узла, который соответствует разбираемому правилу.
                cls = eval(cls)
                # Если csl не является абстрактным классом, в нашем случае это EvalNode, ValueNode, ExprNode,
                # определяется метод parse_action.
                if not inspect.isabstract(cls):
                    # Этот метод вернёт экземпляр класса, который соответствует разбираемому правилу.
                    def parse_action(s, loc, toks):
                        return cls(self._locs[loc][0], self._locs[loc][1], *toks)
                    # Задаётся действие при успешном распознавании текущего правила - вызов функции parse_action.
                    rule.setParseAction(parse_action)

    def parse(self, code: str) -> BlockStatementNode:
        """
        Функция, принимающая строку,
        в которой парсер по заданным правилам будет распознавать элементы описанного языка.
        """

        code = self.close_block(code)

        if "for" and "in" in code:
            code = self.replace_for(code)

        row, col = 0, 0
        for ch in code:
            if ch == '\n':
                row += 1
                col = 0
            elif ch == '\r':
                pass
            else:
                col += 1
            self._locs.append((row, col))
        return self.grammar.parseString(str(code))[0]

    def close_block(self, code: str):
        """ Метод закрытия блоков (символ конца блока - }). """

        lines = code.split('\n')
        for l in range(0, len(lines) - 1):
            indent1 = len(lines[l]) - len(lines[l].lstrip())
            indent2 = len(lines[l + 1]) - len(lines[l + 1].lstrip())
            difference = indent1 - indent2
            if ((difference % 4 == 0) & (difference > 0)):
                for k in range(0, difference//4):
                    lines[l] = lines[l] + " }"
        code = ""
        for l in range(0, len(lines)):
            code += lines[l] + "\n"
        return code

    def replace_for(self, code:str):
        """ Метод преобразования цикла for в Python в более удобный вариант. """
        lines = code.split('\n')
        regexp = re.compile(r'for\s+\w\s+in')
        for l in lines:
            if regexp.search(l):
                codetemp = l[l.index(':') + 1:len(l)]
                range = l[l.index('(') + 1:l.index(')')].split(',')
                l.strip()
                variables = l.split(' ')
                variable = variables[1]
                if (len(range) == 1):
                    for_loop = "for (var " + variable + "=0;" + variable + "<" + range[0] + ";" + variable + "++):"
                    lines[lines.index(l)] = for_loop + codetemp
                if (len(range) == 2):
                    for_loop = "for (var " + variable + "=" + range[0] + ";" + variable + "<" + range[
                        1] + ";" + variable + "++):"
                    lines[lines.index(l)] = for_loop + codetemp
                if (len(range) == 3):
                    for_loop = "for (var " + variable + "=" + range[0] + ";" + variable + "<" + range[
                        1] + ";" + variable + "=" + variable + "+" + range[2] + "):"
                    lines[lines.index(l)] = for_loop + codetemp
        code = ""
        for l in lines:
            code += l + "\n"
        return code




