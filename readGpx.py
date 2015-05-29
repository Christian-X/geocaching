#!/usr/bin/python


import xml.sax
import xml.sax.handler
import geo

home=geo.xyz(51.059146, 13.767000)

shortType={
           u'Earthcache':u'E',
           u'Virtual Cache':u'V', 
           u'Cache In Trash Out Event':u'CITO', 
           u'Unknown Cache':u'?', 
           u'Multi-cache':u'M', 
           u'Event Cache':u'EV', 
           u'Wherigo Cache':u'WIG', 
           u'Letterbox Hybrid':u'L', 
           u'Traditional Cache':u'T',
           u'Webcam Cache':u'WEB'
}

class Cache:
    name=""
    code=""
    found=""
    ctype=""
    hidden=""
    d=""
    t=""
    lon=0
    lat=0
    distance=None
    available=True
    
    def setAvailable(self,available):
        self.available=available
        
    def getDisabled(self):
        return not self.available
    
    def getShortType(self):
        if self.ctype in shortType:
            return shortType[self.ctype]
        return self.ctype
    def getDistance(self):
        global home
        if self.distance==None:
            this=geo.xyz(self.lat,self.lon)
            distance=int(geo.distance(this,home))
            if distance>10000:
                self.distance="%s km"%(distance/1000,)
            else:
                self.distance="%s m"%(distance,)
        return self.distance
    def getAngle(self):
        return int(geo.great_circle_angle(self.getXYZ(),home,geo.magnetic_northpole))
    def getAngleName(self):
        return geo.direction_name(self.getAngle())
    
    def getXYZ(self):
        return geo.xyz(self.lat,self.lon)
    def distanceTo(self,other):
        return int(geo.distance(self.getXYZ(),other.getXYZ()))

    def setLon(self,lon):
        self.lon=lon
    def setLat(self,lat):
        self.lat=lat
    def setCode(self,code):
        self.code=code
    def setName(self,name):
        self.name=name
    def setD(self,d):
        self.d=d
    def setT(self,t):
        self.t=t
    def setType(self,ctype):
        self.ctype=ctype
    def setHidden(self,hidden):
        self.hidden=hidden
    def setFound(self,found):
        if found:
            found=found[0:10]
        self.found=found

class Handler(xml.sax.ContentHandler):
    
    current=None
    allCaches=[]
    parsingLog=False
    parsingCache=False
    inTravelBug=False
    
    nextContentsTo=None
    
    def __init__(self):
        xml.sax.ContentHandler.__init__(self)
    
    def startElement(self,name,attrs):
        if name=="wpt":
            self.current=Cache()
            if "lon" in attrs:
                self.current.setLon(float(attrs["lon"]))
            if "lat" in attrs:
                self.current.setLat(float(attrs["lat"]))
        if self.current==None:
            return
        if name=="groundspeak:travelbug":
            self.inTravelBug=True
        if self.inTravelBug:
            return
        if name=="name":
            self.nextContentsTo=self.current.setCode
        if name=="time":
            self.nextContentsTo=self.current.setHidden
        if name=="groundspeak:name":
            self.nextContentsTo=self.current.setName
        if name=="groundspeak:difficulty":
            self.nextContentsTo=self.current.setD
        if name=="groundspeak:terrain":
            self.nextContentsTo=self.current.setT
        if name=="groundspeak:log":
            self.parsingLog=True
        if name=="groundspeak:cache":
            self.parsingCache=True
            if "available" in attrs:
                self.current.setAvailable(attrs["available"]=="True")
        if self.parsingCache:
            if name=="groundspeak:type":
                self.nextContentsTo=self.current.setType
        if self.parsingLog:
            if name=="groundspeak:type":
                self.nextContentsTo=self.parseLogType
            if name=="groundspeak:date":
                self.nextContentsTo=self.parseLogDate
            if name=="groundspeak:finder":
                self.nextContentsTo=self.parseLogFinder
    def parseLogType(self,content):
        self.logType=content
    def parseLogDate(self,content):
        self.logDate=content
    def parseLogFinder(self,content):
        self.logFinder=content

    collect=""
    
    def characters(self,content):
        if self.nextContentsTo:
            self.collect=self.collect+content

    def endElement(self,name):
        if self.nextContentsTo:
            self.nextContentsTo(self.collect)
            self.nextContentsTo=None
        self.collect=""
        if name=="groundspeak:travelbug":
            self.inTravelBug=False
            
        if name=="wpt":
            self.allCaches.append(self.current)
            self.current=None
        if name=="groundspeak:log":
            self.parsingLog=False
            if self.logType in ("Found it","Attended") and self.logDate and self.logFinder=="Lemarasic":
                self.current.setFound(self.logDate)
            self.logType=None
            self.logDate=None
        
def readGpx(name):
    myReader=Handler()
    xml.sax.parse(name,myReader)
    return myReader.allCaches
            
            
        
#myReader=Handler()#
#xml.sax.parse("14905626.gpx",myReader)
#for c in myReader.allCaches:
#    print ("%s: %s/%s %s %s %s"%(c.code,c.d,c.t,c.name,c.found,c.hidden))
