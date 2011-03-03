#!/usr/bin/env python

import sys

file = open("handlers.py")

lines = file.read()

output = [a.strip() for a in lines.split('\n')]

output = [a.strip() for a in output if (a.startswith('API') | a.startswith('class'))]

newfile = open(sys.argv[1], 'w')

for line in output:
    if line.startswith('class'):
        newfile.write('\n' + line + '\n')
    else:
        newfile.write(line+'\n')
        
newfile.close()
file.close()