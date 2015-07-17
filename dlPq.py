#!/usr/bin/python3
import api
import sys
a=api.GeocachingAPI()
a.login("lemarasic",sys.argv[1])
pqs=a.listPQs()
if len(sys.argv)==2:
    for p in pqs:
        print(p.name)

if len(sys.argv)==4:
    searchFor=sys.argv[2]
    saveAs=sys.argv[3]
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
        
            