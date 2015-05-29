import requests
from lxml import html
import json
import re
import logging

MAXIMUM_SYNC=54

def transferViewstates(tree,params):
    count=tree.get_element_by_id("__VIEWSTATEFIELDCOUNT",None)
    params["__VIEWSTATE"]=tree.get_element_by_id("__VIEWSTATE").value
    if count:
        count=int(count)-1
        for i in 1..count:
            field="__VIEWSTATE%d"%(i,)
            params[field]=tree.get_element_by_id(field).value
            
        
 
MC_API_BASE="https://communication-service.geocaching.com/api/"

def mcUrl(append):
    return "%s%s"%(MC_API_BASE,append)


class Cache(object):
    def __init__(self):
        self.storage={}
    def store(self,key,result):
        self.storage[key]=result
    def get(self,key):
        if key in self.storage:
            return self.storage[key]
        return None

class PQ(object):
    def __init__(self,name,url,date,api):
        self.name=name
        self.url="https://www.geocaching.com"+url
        self.date=date
        self.api=api
    def download(self,fname):
        response=self.api.session.get(self.url,stream=True)
        if not response.ok:
            raise Exception("Could not download")
        with open(fname,'wb') as fd:
            for block in response.iter_content(1024):
                fd.write(block)
        
bigSession=requests.Session()

class GeocachingAPI(object):
    def login(self,user,pw):
        self.cache=Cache()
        self.session=requests.Session()
        login1=self.session.get("https://www.geocaching.com/login/default.aspx")
        if login1.status_code!=200:
            raise Exception("could not login %s "%(login1.status_code,))
        tree=html.fromstring(login1.text)
        params={"__EVENTTARGET":"",
            "__EVENTARGUMENT":"",
            "ctl00$ContentBody$tbUsername":user,
            "ctl00$ContentBody$tbPassword": pw,
            "ctl00$ContentBody$cbRememberMe": "on",
            "ctl00$ContentBody$btnSignIn": "Login"}
        transferViewstates(tree,params)
        login2=self.session.post("https://www.geocaching.com/login/default.aspx",data=params)
        #Todo: validate sucessfull
        self.getMessageCenterToken()
    def listPQs(self):
        result=[]
        page=self.session.get("https://www.geocaching.com/pocket")
        tree=html.fromstring(page.text)
        pqs=tree.xpath("//table[@id='uxOfflinePQTable']/tr")
        for row in pqs:
            name=row.xpath("td/a/text()")
            href=row.xpath("td/a/@href")
            date=row.xpath("td[5]/text()")
            if len(name)==1:
                name=str(name[0]).strip()
            else:
                print("NoName")
                continue
            if len(href)==1:                
                href=str(href[0])
            else:
                print("NoLink")
                continue
            if len(date)==1:
                date=str(href[0]).strip()
            else:
                date=""
            result.append(PQ(name,href,date,
              self))
        return result
        
    def getMessageCenterToken(self):
        mc=self.session.get("https://www.geocaching.com/account/messagecenter")
        self.mcParams=json.loads(re.search("serverParams = \[(.*)\]\[0\];",mc.text).group(1))
        token=self.session.post("https://www.geocaching.com/account/messagecenter/home/getaccesstoken",data="{}",headers={"X-Verification-Token":self.mcParams['reqToken']})
        if token.status_code!=200:
            raise Exception("could not get token %s"%(token,))
        self.mcToken=json.loads(token.text)
        
    def getMcHeader(self,key=None,noCache=False):
        headers={"Authorization":"bearer %s"%(self.mcToken,)}
        if key and not noCache:
            etag=self.cache.get(key)
            headers['If-None-Match']=etag
        return headers
    
    def genericGet(self,path,key=True,noCache=False,raw=False,data=None):
        if key==True:
            key=path
        result=bigSession.get(mcUrl(path),headers=self.getMcHeader(key,noCache),params=data)
        bigSession.cookies.clear()
        if result.status_code==304:
            return None
        if result.status_code!=200:
            raise Exception("could not get conversation summary")
        if key and "etag" in result.headers:
            self.cache.store(key,result.headers['etag'])
        if raw:
            return result
        if result==None:
            return None
        return json.loads(result.text)
        
    
    def getConversations(self,noCache=False):
        return self.genericGet("conversation",noCache=noCache)
    
    def getMessages(self,convid,take=10,noCache=False):
        return self.genericGet("conversation/%s/message?take=%d"%(convid,take))
    def postMessage(self,convid,message):
        r=requests.post(mcUrl("conversation/%s/message"%(convid)),headers=self.getMcHeader(),data=json.dumps({"message":message}))
        return r
    
    def searchUsers(self,username):
        return self.genericGet("accountsummary",data={"usernameStartsWith":username},noCache=True)
    def getConversationByParticipant(self,participantId):
        return self.genericGet("conversation",data={"participantIds":participantId},noCache=True)
    def createConversation(self,participantId):
        r=requests.post(mcUrl("conversation"),headers=self.getMcHeader(),data=json.dumps({"participants":[{"accountId":participantId}]}))
        if r.ok:
            return json.loads(r.text)
        
        
        
##
## PUT conversation/$convId$/participant/$accountId$
##{"accountId":"dc672d13-49c6-4901-8fec-02bf1ed5018d","conversationId":"f364da80-511c-4e1d-b2e1-9dcf8a04c1e4","lastViewedMessageId":"635683131202883192","createDate":"2015-05-27T08:38:01.271Z","isVisible":true,"profileImageUrl":"https://www.geocaching.com/images/default_avatar.jpg","username":"mctest","securityType":"Public"}
## ==>lastViewedMessageId
##
    
    
class MCUser(object):

    def __init__(self,username,uuid):
        self.username=username
        self.uuid=uuid
        self.convId=None
        self.profileImageUrl=None
        self.lastMessageViewed={}
        
    def setAll(self,store):
        self.username=store['username']
        self.uuid=store['uuid']
        self.convId=store['convId']
        self.profileImageUrl=store['profileImageUrl']
    def __str__(self):
        return "[%s@%s]"%(self.username,self.convId)
        
    def bareStore(self):
        return {"username":self.username,
                "uuid":self.uuid,
                "convId":self.convId,
                "profileImageUrl":self.profileImageUrl}
                
class Conversation(object):
    def __init__(self,convid=None):
        self.convid=convid
        self.lastSeenId=0
        
    def setAll(self,store):
        self.convid=store['id']
        self.lastSeenId=store['lastSeenId']
        
    def bareStore(self):
        return {"id":self.convid,
                "lastSeenId":self.lastSeenId}

class MessageCenterLogic(object):

    def __init__(self,user,pw):
        self.messageReceivedCallback=None
        self.messageViewedCallback=None
        self.logger=logging.getLogger("MessageCenter[%s]"%(user,))
        self.user=user
        self.pw=pw
        self.api=GeocachingAPI()
        self.myId=""
        self.users={}
        self.users2={}
        self.convs={}
        self.thisUser=None
        self.selfSentMessages=[]
        self.lastViewedUpdates={}

    def updateLastViewed(self,convId,mId):
        if convId in self.lastViewedUpdates:
            if int(self.lastViewedUpdates[convId])>int(mId):
                return
        self.lastViewedUpdates[convId]=mId
        
    def getUserByName(self,username,lookUp=True):
        if username.lower() in self.users:
            return self.users[username.lower()]
        if lookUp:
            result=self.lookUpUser(username)
            if result:
                user=MCUser(result['username'],result['publicGuid'])
                user.profileImageUrl=result['avatarUrl']
                self.addUser(user)
                return user
        
    def lookUpUser(self,username):
        response=self.api.searchUsers(username)
        if response:
            for user in response:
                if user['username']==username:
                    return user
                
    def getUserById(self,uid):
        if uid==self.myId:
            return self.thisUser
        if uid in self.users2:
            return self.users2[uid]
        raise Exception("Do not know user %s"%(uid,))
    
    def addUser(self,user):
        self.users[user.username.lower()]=user
        self.users2[user.uuid]=user
        
        
    def login(self):
        self.api.login(self.user,self.pw)
        self.myId=self.api.mcParams["accountPublicGuid"]
        self.thisUser=MCUser(self.user,self.myId)
    
    def store(self):
        return {"users":[u.bareStore() for u in self.users.values()],
                "conversations":[c.bareStore() for c in self.convs.values()]}
                           
    def bootstrap(self,store):
        for _user in store["users"]:
            user=MCUser(None,None)
            user.setAll(_user)
            self.addUser(user)
            
        for _conv in store["conversations"]:
            conv=Conversation()
            conv.setAll(_conv)
            self.convs[conv.convid]=conv
            self.logger.debug("Learnt about Conversation %s lastKey %d"%(conv.convid,conv.lastSeenId))
        
    
    def learnUser(self,participiant,convId=None):
        if participiant['accountId']==self.myId:
            return
        if not participiant['username'].lower() in self.users:
            user=MCUser(participiant['username'],participiant['accountId'])
            user.profileImageUrl=participiant['profileImageUrl']
            self.addUser(user)
        if convId:
            self.users[participiant['username'].lower()].convId=convId
            
    def onMessageReceived(self,mid,mtext,mfrom,mdate,mattachments):
        if self.messageReceivedCallback:
            self.messageReceivedCallback(mid,mtext,mfrom,mdate,mattachments)
        else:
            print("NEW MESSAGE: [%s] %s> %s [@%s [%s"%(mid,mfrom.username,mtext,mdate,mattachments))
            
    def onMessageViewed(self,mid,convid,mwho):
        if self.messageViewedCallback:
            self.messageViewedCallback(mid,convid,mwho)
        else:
            print("%s has viewed messages up to %s"%(mwho,mid))
            
    def postLastViewedUpdate(self,conversation):
        convId=conversation['id']
        self.logger.debug("Last viewed message shall be updated for %s"%(convId,))
        for participant in conversation['participants']:
            if participant['accountId']==self.myId:
                if int(participant['lastViewedMessageId'])<int(self.lastViewedUpdates[convId]):
                    headers=self.api.getMcHeader()
                    headers['Content-Type']="application/json"
                    participant['lastViewedMessageId']="%s"%(self.lastViewedUpdates[convId])
                    bigSession.put(mcUrl("conversation/%s/participant/%s"%(convId,self.myId)),data=json.dumps(participant),headers=headers)
                else:
                    self.logger.warn("Should update lastViewed, but already newer...")
                del self.lastViewedUpdates[convId]
        
    def updateConv(self,conversation):
        convId=conversation['id']
        self.logger.debug("==<%s"%(self.convs,))
        if not convId in self.convs:
            self.logger.debug("New Conversation %s"%(convId,))
            self.convs[convId]=Conversation(convId)
            for participant in conversation['participants']:
                self.learnUser(participant,convId)
            self.logger.debug("==>%s"%(self.convs,))
        conv=self.convs[convId]
        self.logger.debug("Checking Conv %s"%(convId))
        for participant in conversation['participants']:
            if participant['accountId']==self.myId:
                continue
            if not participant['lastViewedMessageId']:
                continue
            localUser=None
            if participant['accountId'] in self.users2:
                localUser=self.getUserById(participant['accountId'])
            if not localUser:
                self.logger.error("Could not map user in existing conversation")
                continue
            if not convId in localUser.lastMessageViewed:
                localUser.lastMessageViewed[convId]=0
            if int(participant['lastViewedMessageId'])>localUser.lastMessageViewed[convId]:
                self.onMessageViewed(participant['lastViewedMessageId'],convId,localUser)
                localUser.lastMessageViewed[convId]=int(participant['lastViewedMessageId'])
        if convId in self.lastViewedUpdates:
            self.postLastViewedUpdate(conversation)
            
        if conv.lastSeenId<int(conversation['lastMessageId']):
            toTake=2
            if conv.lastSeenId==0:
                toTake=MAXIMUM_SYNC
            inSync=False
            messages=[]
            while not inSync:
                messages=self.api.getMessages(convId,take=toTake)
                oldestKey=int(messages[-1]['id'])
                self.logger.debug("oldestKey,newestKey,lastSeenId (%s,%s,%s)"%(oldestKey,messages[0]['id'],conv.lastSeenId))
                if oldestKey<=conv.lastSeenId:
                    inSync=True
                else:
                    if toTake==MAXIMUM_SYNC:
                        break
                    toTake=toTake*3
                    if toTake>MAXIMUM_SYNC:
                        toTake=MAXIMUM_SYNC
            for message in messages[::-1]:
                if int(message['id'])>conv.lastSeenId:
                    if not message['id'] in self.selfSentMessages:                    
                        self.onMessageReceived(message['id'],message['messageText'],self.getUserById(message['createdBy']),message['createDate'],message['attachments'])
                    else: 
                        print("Self sent message %s - skipping "%(message['id'],))
                    conv.lastSeenId=int(message['id'])
            
    def sendMessage(self,username,message):
        user=self.getUserByName(username)
        if not user:
            raise Exception("Can not find %s"%(username,))
        if user.convId==None:
            newConv=self.api.getConversationByParticipant(user.uuid)
            user.convId=newConv['id']
        response=self.api.postMessage(user.convId,message)
        #TODO: Check error
        if response.ok:
            result=json.loads(response.text)
            self.selfSentMessages.append(result['id'])
            return result['id']
            
    
    def poll(self):
        noCache=False
        if len(self.lastViewedUpdates)>0:
            noCache=True
            self.logger.debug("Updates Pending, disable cache")
        conversations=self.api.getConversations(noCache=noCache)
        if conversations:
            for conv in conversations:
                self.updateConv(conv)
                
            
            
    
        
