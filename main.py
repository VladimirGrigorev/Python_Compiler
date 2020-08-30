import os
from src.AST.Parser import *
from src.Semantics.semantic_analyzer import *
from src.Сompiler.code_generator import *
from src.VM.VirtualMachine import *

# строка с кодом, который в последствии будет распознаваться парсером.
prog = '''
b = 1
a = b + 2
print(a) # comment

str = "Hello " + "world"
print(str)

bool = a < b
print(bool)

if a > b :
    a = 7
print(a)

while a < 10 :
    a++
    print(a)
    
def sum(a, b):
    return a + b    
print(sum(a, 5))


'''
# вызов конструктора класса Parser.
parser = Parser()
# вызов конструктора класса Analyzer.
analyzer = Analyzer()
# в переменной res хранится корень графа, описывающего структуру кода из переменной prog.
res = parser.parse(prog)
print(*res.tree, sep=os.linesep)

# вызов метода analyze, который производит семантический анализ
# analyzer.analyze(res)
# if len(analyzer.errors) > 0:
#     for e in analyzer.errors:
#         print("Ошибка: {}".format(e.message))
# else:
# print("Ошибок не обнаружено.")
generator = CodeGenerator(res)
generator.print_bytecode()
vm = VirtualMachine(generator.lines)


