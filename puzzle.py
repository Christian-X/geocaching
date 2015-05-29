#!/usr/bin/python3
import readGpx
import sys
import itertools
import os
import time

checkTime=False
caches=[]
readCodes=set()  
for f in sys.argv[1:]:
    print("Reading %s"%(f,),file=sys.stderr)
    newlyRead=readGpx.readGpx(f)
    for c in newlyRead:
        if not c.code in readCodes:
            caches.append(c)
            readCodes.add(c.code)
            
print("%d Caches read "%(len(caches),),file=sys.stderr)
#onlyCaches=["GCPBCT","GC37ZMX","GCQNK6","GCV18A","GCYGRJ","GC5FD02","GC2HEA","GC37ZMX","GCR05G","GCVW6Y","GCKDNF5","GCNTQ9","GC5M4XP","GCWECD","GC10V3F","GCYGRJ","GC2K86B","GC5M4XP","GCVDF6","GCJHNE","GC2CY97","GC3GQBA","GCTZ18"]
#onlyCaches=["GC5T2GE","GC18WCX","GCNK6F","GCVADM","GC3YZB9","GCQ7PJ"]
#onlyCaches=["GC5M4XP","GCJAET","GCWH86","GC2KVR0","GC3Y7CD","GCG1QB"]
#onlyCaches=["GC2X8PF","GC4TJ0A","GCNRZK","GC56BH9","GCM7QV","GCWECD","GCYG31"]

def noDups(c):
 #   return c.code in onlyCaches
    chars=set()    
    if c.found!="" and not checkTime:
        return False
    for char in c.code[2:]:
        if char in chars:
            return False
        chars.add(char)
    return True
    
    
caches=list(filter(noDups,caches))

print("%d Caches after filter "%(len(caches),),file=sys.stderr)
startIndex=0
longSoFar=""
checked=0
lastPoint=0

class Match(object):
    def __init__(self,caches,distance,num):
        self.caches=caches
        self.distance=distance
        self.num=num

    def printHtml(self,fd=sys.stdout):
        print("<table>",file=fd)
        print ("<tr class='combis'><td colspan='6' > %d Kombinationen</td></tr>"%(self.num,),file=fd)
        for c in self.caches:
            CSSClass=""
            if c.getDisabled():
                CSSClass="cache_disabled"
            if c.found!="":
                CSSClass=CSSClass+" cache_found"
            print ("<tr class='%s'><td><a href='http://coord.info/%s'>%s</a></td><td>%s</td><td>%s</td><td>%s</td><td>D%s/T%s</td><td>%s</td><td>%s %s</td></tr>"%(CSSClass,c.code,c.code,c.getShortType(),c.name,c.found,c.d,c.t,c.getDistance(),c.getAngle(),c.getAngleName()),file=fd)
        print("<tr class='sum'><td colspan='6'>%s m</td></tr>"%(self.distance,),file=fd)
        print("</table>",file=fd)
        
def outputAll():
    founds.sort(key=lambda x: x.distance)
    with open("output.html","w") as fd:
        print( "<!DOCTYPE HTML>",file=fd)
        print ("<html><head><meta charset='utf-8'><title>...</title><link rel='stylesheet' href='main.css'></head><body>",file=fd)
        for c in founds:
            c.printHtml(fd)
            print("</body></html>",file=fd)
founds=[]


globaliter=0
startTime=time.time()
def search(startIndex,soFar,found,checkTime,caches):
    def myprint(text):
        print ((" "*len(found)),text)
    global longSoFar
    global checked
    global lastPoint
    global founds
    global globaliter
    if len(found)==1:
        print ("%s of %s"%(startIndex,len(caches)))
        duration=time.time()-startTime
        if duration>0 and startIndex!=len(caches):
            estimation=(duration/(startIndex+1))*(len(caches)-startIndex)
            print ("%s s took, estimated %s till end"%(int(duration),int(estimation)))
    globaliter=globaliter+1
    localiter=globaliter
    soFar2="".join(c.code[2:] for c in found)
#    myprint ("search#%d(%s,%s,%s,%s)"%(localiter,startIndex,soFar," ".join(c.code for c in found),len(caches)))
    if len(soFar2)!=len(soFar):
        print("OUCH OUCH OUCH %s %s"%(soFar,soFar2))
        sys.exit(-1)
    soFar=''.join(sorted(soFar))
    if len(soFar)>len(longSoFar):
        myprint ("<!--Longest: %s %d %s-->"%(soFar,len(soFar)," ".join(c.code for c in found)))
        longSoFar=soFar
    if len(soFar)==31:
        distanceSorted=[]
        unsorted=[]+found
        unsorted.sort(key=lambda x:x.found=="")
        distanceSorted.append(unsorted.pop(0))
        while (len(unsorted)>=1 and distanceSorted[-1].found!=""):
            distanceSorted.append(unsorted.pop(0))
        totalDistance=0
        while len(unsorted)>=1:
            unsorted.sort(key=lambda x: x.distanceTo(distanceSorted[-1]))
            distanceSorted.append(unsorted.pop(0))
        last=None
        for el in distanceSorted:
            if el.found=="":
                if last:
                    totalDistance=totalDistance+el.distanceTo(last)
                last=el
                
        founds.append(Match(distanceSorted,totalDistance,checked))
        print ("MATCH ["," ".join(c.code for c in distanceSorted),"]","[++"," ".join(c.code for c in unsorted))
        if (len(founds)%15==0 or len(founds)<10):
            outputAll()
        return
    
    possibleCombis=[]        
    while startIndex<len(caches):
        checked=checked+1
        timeValid=True
        if checkTime:
            timeValid=False
            times=(c.found for c in found)
            if caches[startIndex].found and caches[startIndex].found in times:
                timeValid=True
        noDups=True
        for c in caches[startIndex].code[2:]:
            if c in soFar:
                noDups=False
#                print ("%s is in %s ?!"%(c,soFar))
#                print ("%d %s colides with %s"%(startIndex,caches[startIndex].code," ".join(c.code for c in found)))
                break
        if noDups:
            possibleCombis.append(caches[startIndex])
        startIndex=startIndex+1
    newI=0
    for c in possibleCombis:
        search(newI,soFar+c.code[2:],found+[c],not timeValid,possibleCombis)
        newI=newI+1

#        if noDups==True and len(soFar)<31:
#            myprint ("Deeper Search @%d"%(startIndex,))
#            search(startIndex,soFar+caches[startIndex].code[2:],found+[caches[startIndex]],not timeValid)
#    myprint("End Of Search#%d"%(localiter,))
    
        
seed=[]
seedcodes=[]
sofar=""
for c in caches:
    if c.code in seedcodes:
        seed.append(c)
        print("Found seed %s %s "%(c.code,c.name))
        sofar=sofar+c.code[2:]

        
search(0,sofar,seed,checkTime,caches)

outputAll()