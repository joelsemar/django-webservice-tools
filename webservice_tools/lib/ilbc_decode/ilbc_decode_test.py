#!/usr/bin/env python

print "Starting"
import py_ilbc_decode
print "Imported"
infile = open('wholething.lbc', 'rb')
data = infile.read()

result = py_ilbc_decode.decode(20, data)
print "ran decode"
outfile = open('wholething.pcm', 'wb')

for datum in result:
    outfile.write(datum);
    
outfile.close()
infile.close()
