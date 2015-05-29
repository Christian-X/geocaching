#!/usr/bin/python3
import api
import sys
a=api.GeocachingAPI()
a.login("lemarasic","cache4us")
pqs=a.listPQs()
if len(sys.argv)==1:
    for p in pqs:
        print(p.name)

if len(sys.argv)==3:
    searchFor=sys.argv[1]
    saveAs=sys.argv[2]
    numFound=0
    pqFound=0
    for p in pqs:
        if p.name.find(searchFor)!=-1:
            numFound=numFound+1
            pqFound=p
    if numFound!=1:
        print("No (sure) match")
    else:
        pqFound.download(saveAs)
        
            