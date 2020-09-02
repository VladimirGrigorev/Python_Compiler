import os
from src.AST.Parser import *
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
    if a == 9 :
        print("nine")
        
for i in range(1,10):
    print(i)
    
def sum(a, b):
    return a + b    
print(sum(a, 5))
'''

# вызов конструктора класса Parser.
parser = Parser()
# в переменной res хранится корень графа, описывающего структуру кода из переменной prog.
res = parser.parse(prog)
print(*res.tree, sep=os.linesep)

generator = CodeGenerator(res)
generator.print_bytecode()
vm = VirtualMachine(generator.lines)


