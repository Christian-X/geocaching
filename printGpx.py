#!/usr/bin/python3
import readGpx
import sys

caches=readGpx.readGpx(sys.argv[1])

for c in caches:
    disable=" "
    if c.getDisabled():
        disable="!"
    print ("%s%s(%s) %s/%s %s %s %s %s N%s E%s"%(disable,c.code,c.getShortType(),c.d,c.t,c.hidden,c.found,c.name,c.getDistance(),c.lon,c.lat))
    
