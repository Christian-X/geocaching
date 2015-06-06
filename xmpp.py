
import logging
import sleekxmpp
import json

from sleekxmpp.componentxmpp import ComponentXMPP
from sleekxmpp.stanza import Error
from sleekxmpp.xmlstream.matcher import MatchXPath,StanzaPath
from sleekxmpp.xmlstream.handler import Callback

import threading
import api
import base64
import xep_0333

def isBot(stanza):
    return stanza['to'].user==config.bot.user


class AUser(object):
    def __init__(self,jid,xmpp):
        self.jid=jid
        self.logger=logging.getLogger("AUser.*")
        self.active=True
        self.online=False
        self.gcUser=None
        self.gcPass=None
        self.mcConnection=None
        self.storedConnection=None
        self.lastPoll=0
        self.xmpp=xmpp
        self.idMap={}

    def speak(self,message):
        self.xmpp.speak(self,message)
    
    def mapId(self,user,xmppId,mcId):
        if not user in self.idMap:
            self.idMap[user]={}
        self.idMap[user][mcId]=xmppId
    def lookUpId(self,user,mcId):
        if not user in self.idMap:
            return None
        if not mcId in self.idMap[user]:
            return None
        return self.idMap[user][mcId]

    def forgetIds(self,user):
        if user in self.idMap:
            del self.idMap[user]
            
    def forgetIdsUpTo(self,user,convId):        
        if user in self.idMap:
            lidMap=self.idMap[user]
            newMap={}
            for key in lidMap:
                if key>convId:
                    newMap[key]=lidMap[key]
            self.idMap[user]=newMap
        
        
    def load(self,stringordict):
        if isinstance(stringordict,str):
            store=json.loads(stringordict)
        else:
            store=stringordict
        
        self.logger=logging.getLogger("AUser.%s"%(self.jid,))
        if "jid" in store:
            self.jid=sleekxmpp.JID(store["jid"])
        if "active" in store:
            self.active=store["active"]
        if "gcUser" in store:
            self.gcUser=store["gcUser"]
        if "gcPass" in store:
            self.gcPass=base64.b64decode(store["gcPass"].encode('utf-8')).decode('utf-8')
        if "mcBoot" in store:
            self.storedConnection=store["mcBoot"]
        self.logger.debug("Retrieved %s from store, mcBoot= %s"%(self.jid,self.storedConnection))

    def store(self):
        store={"jid":self.jid.bare,
            "active":self.active}
        if self.gcUser:
            store["gcUser"]=self.gcUser
        if self.gcPass:
            store["gcPass"]=base64.b64encode(self.gcPass.encode('utf-8')).decode('utf-8')
        if self.mcConnection:
            self.storedConnection=self.mcConnection.store()
        if self.storedConnection:
            store["mcBoot"]=self.storedConnection
            
        return store

    def messageDisplayed(self,message):
        if self.mcConnection==None:
            return False
        toMcUser=self.mcConnection.getUserById(message['to'].user)
        if not toMcUser:
              return False
        if not toMcUser.convId:
            return False
        self.mcConnection.updateLastViewed(toMcUser.convId,message['cm_displayed'])
        
    def handleMessage(self,message):
        if self.mcConnection==None:
            return False
        toMcUser=self.mcConnection.getUserById(message['to'].user)
        if not toMcUser:
            return False
        if not message['body']:
            self.logger.debug("No body in message")
            return
        if message['request_receipt'] and not message['receipt']:
            ack=self.xmpp.Message()
            ack['from']=message['to']
            ack['to']=message['from']
            ack['receipt']=message['id']
            ack.send()
        if message['cm_markable']:
            ack=self.xmpp.Message()
            ack['from']=message['to']
            ack['to']=message['from']
            ack['cm_received']=message['id']
            ack.send()

        mcId=self.mcConnection.sendMessage(toMcUser.username,message['body'])
        if mcId:
            if message['id']:
                self.mapId(message['to'].user,message['id'],mcId)
            return True
        return False
        
        
    def setOnline(self):
        self.online=True
        if self.gcUser and self.gcPass:
            self.mcConnection=api.MessageCenterLogic(self.gcUser,self.gcPass)
            self.mcConnection.messageReceivedCallback=self.onMCMessageReceived
            self.mcConnection.messageViewedCallback=self.onMCMessageViewed
            if self.storedConnection:
                self.logger.debug("BootStrapping")
                self.mcConnection.bootstrap(self.storedConnection)
            self.logger.debug("Login")
            self.login()
        else:
            self.speak("Hello. You need to set user & password")
    def logout(self):
        if self.mcConnection:
            storedConnection=self.mcConnection.store()
            self.mcConnection=None
        
    def login(self):
        if self.mcConnection:
            self.mcConnection.login()
            self.speak("Login as %s successfull"%(self.gcUser,))
            self.updatePresence()
            
    def updatePresence(self):
        for user in self.mcConnection.users.values():
            try:
                presence=self.xmpp.Presence()
                presence['from']=self.makeJid(user)
                presence['to']=self.jid
                presence['type']='available'                
                presence.send()
                nickMsg=self.xmpp.Message()
                nickMsg['from']=self.makeJid(user)
                nickMsg['to']=self.jid
                nickMsg['nick']=user.username
                nickMsg.send()
            except sleekxmpp.jid.InvalidJID:
                pass
    

    def makeJid(self,mcUser):
        return sleekxmpp.JID("%s@gc.geheimergarten.de"%(mcUser.uuid,))

    def onMCMessageViewed(self,mid,convid,mwho):
        try:
            msgFrom=self.makeJid(mwho)
        except sleekxmpp.jid.InvalidJID:
            self.logger.debug("displayed// Invalid JID %s"%(mwho,))
            return
        xmppId=self.lookUpId(msgFrom.user,mid)
        if xmppId:
            marker=self.xmpp.Message()
            marker['from']=msgFrom
            marker['to']=self.jid
            marker['cm_displayed']=xmppId
            marker.send()
        else:
            self.logger.debug("Could not look up Message Id %s"%(mid,))
        
        
    def onMCMessageReceived(self,mid,mtext,mfrom,mdate,mattachments):
        if mfrom==self.mcConnection.thisUser:
            self.logger.warn("Message from self can't be handled")
            self.speak("You spoke to someone : %s "%(mtext,))
            return
        msg=self.xmpp.Message()
        msg['to']=self.jid
        msg['id']=mid
        msg['nick']=mfrom.username
        try:
            msg['from']=self.makeJid(mfrom)
        except sleekxmpp.jid.InvalidJID as e:
            self.speak("illegal username in xmpp:%s > %s"%(mfrom,mtext))
            return
        msg['delay']['stamp']=mdate
        if mtext:
            msg['body']=mtext
        if mattachments:
            for att in mattachments:
                msg['body']=msg['body']+att['url']
        msg['cm_markable']=True
        msg.send()
        

        
    def setOffline(self):
        self.online=False
        self.logout()
        
    def poll(self):
        if self.online and self.mcConnection:
            self.mcConnection.poll()
                        
            
            
class Config(object):
    COMPONENT_NAME="tbd"
    COMPONENT_SECRET="tbd"
    
    def __init__(self):
        self.users=[]
        self.calcId()
        self.toXmpp=None
        
    def calcId(self):
        self.bot=sleekxmpp.JID(self.COMPONENT_NAME+"/bot")


    def setToXmpp(self,toXmpp):
        self.toXmpp=toXmpp
        
    def store(self):
        toStore={"COMPONENT_NAME":  self.COMPONENT_NAME,
                 "COMPONENT_SECRET":self.COMPONENT_SECRET,
                 "users":[user.store() for user in self.users]
                 }
        
        f=open("config","w")
        json.dump(toStore,f,indent=4)
        f.close()

    def load(self):
        f=open("config","r")
        myStore=json.load(f)
        if "COMPONENT_NAME" in myStore:
            self.COMPONENT_NAME=myStore["COMPONENT_NAME"]
        if "COMPONENT_SECRET" in myStore:
            self.COMPONENT_SECRET=myStore["COMPONENT_SECRET"]
        if self.toXmpp==None:
            return
        
        if "users" in myStore:
            for userjson in myStore["users"]:
                user=AUser(None,self.toXmpp)
                user.load(userjson)
                self.users.append(user)
        self.calcId()
                
    def delUser(self,jid):
        user=self._lookup(jid)
        if user:
            user.active=False

    def addUser(self,jid):
        user=self._lookup(jid)
        if user:
            user.active=True
        else:
            self.users.append(AUser(jid,self.toXmpp))

    def lookup(self,jid):
        user=self._lookup(jid)
        if user:
            if user.active:
                return user
        return None
    
    def _lookup(self,jid):
        for user in self.users:
            if user.jid.bare==jid.bare:
                return user
        return None
        
        
class MyComponent(ComponentXMPP):
    def  __init__(self,jid,secret,config,server="localhost",port=5347):
        ComponentXMPP.__init__(self,jid,secret,server,port)
        self.add_event_handler("got_online",self.got_online)
        self.add_event_handler("got_offline",self.got_offline)
        self.add_event_handler("message",self.message)
        self.add_event_handler("presence",self.presence)
        self.add_event_handler("receipt_received",self.receipt_received)
        self.add_event_handler("session_start",self.start)
        self.add_event_handler("killed",self.shutdown)
#        self.add_event_handler("disco_info_query",self.info_query)
#        self.add_event_handler("disco_items_query",self.items_query)
        self.register_handler(Callback("cm_displayed",
                                 MatchXPath("{%s}message/{urn:xmpp:chat-markers:0}displayed"%(self.default_ns,)),
                                 self.message_displayed))
        self.logger=logging.getLogger("Component")
        self.config=config
        self.remove_handler('VCardTemp')
        self.register_handler(Callback('MyVCardTemp',
                              StanzaPath('iq/vcard_temp'),
                              self.handleVCard))
        

    def handleVCard(self,iq):
        if iq['type']=='result':
            pass
        if iq['type']=='get':
            if isBot(iq):
                from sleekxmpp.plugins.xep_0054 import VCardTemp
                vcard=VCardTemp()
                vcard['NICKNAME']="JustABot"
                iq.reply()
                iq.append(vcard)
                iq.send()
            else:
                self.logger.debug("ToHandle...")
        
    def start(self,arg):
        self.remove_handler('VCardTemp')
#        vcard=self['xep_0054'].get_vcard(self.config.bot,cached=True)
        #self['xep_0054'].publish_vcard(vcard=vcard,jid=self.config.bot)
        import base64
#        with open("my-avatar.jpg","rb") as fd:
#            self.avatar=fd.read()
#            c['xep_0153'].set_avatar(jid=sleekxmpp.JID("gc.geheimergarten.de"),mtype="image/jpeg",avatar=base64.b64encode(data))


        for user in self.config.users:
            if user.active:
                botPresence=self.Presence()
                botPresence['from']=config.bot
                botPresence['to']=user.jid
                botPresence.send()
                msg=self.Message()
                msg['from']=config.bot
                msg['to']=user.jid
                msg['nick']="GC MessageCenter Control [%s]"%(user.gcUser)
                msg.send()
                botPresence['type']="probe"
                botPresence.send()
        self.schedule("mcpoll",12,self.poll,repeat=True)

    def poll(self):
        for user in self.config.users:
            user.poll()
            
    def shutdown(self,arg):
        self.scheduler.remove("mcpoll")
        self.config.store()
        for user in self.config.users:
            if user.active:
                botPresence=self.Presence()
                botPresence['from']=self.config.bot.bare
                botPresence['type']="unavailable"
                botPresence.send()
        
    def presence(self,presence):
        if isBot(presence):
           #the bot is addressed...
           if presence['type']=='probe':
               result=self.Presence()
               result['to']=presence['from']
               result['from']=self.config.bot
               result['type']="available"
               result.send()
           else:
               if presence['type']=="subscribe":
                   result=self.Presence()
                   result['from']=self.config.bot
                   result['to']=presence['from']
                   result['type']="subscribe"                   
                   result.send()
                   result=self.Presence()
                   result['from']=self.config.bot
                   result['to']=presence['from']
                   result['type']="subscribed"                   
                   result.send()
                   result=self.Presence()
                   result['from']=self.config.bot
                   result['to']=presence['from']
                   result['type']="available"
                   result['status']="Just sitting here..."
                   self.config.addUser(presence['from'])
                   result.send()                   
               elif presence['type']=="unsubscribe":
                   result=self.Presence()
                   result['from']=self.config.bot
                   result['to']=presence['from']
                   result['type']="unsubscribe"
                   result.send()
                   result=self.Presence()
                   result['type']="unsubscribed"
                   result['from']=self.config.bot
                   result['to']=presence['from']
                   self.config.delUser(presence['from'])
                   result.send()
               else:
                   self.logger.warning("Presence not handled... %s",presence)
        else:
            pass
                   
        pass
    def got_online(self,presence):
        user=self.config.lookup(presence['from'])
        if user and user.active:
            user.setOnline()
        else:
            self.logger.debug("Unknown got online...%s"%(presence,))
            
    def got_offline(self,presence):
        user=self.config.lookup(presence['from'])
        if user:
            user.setOffline()

    def speak(self,user,message):
        msg=self.Message()
        msg['from']=self.config.bot
        msg['to']=user.jid
        msg['body']=message
        msg.send()
        
        
    def botMessage(self,message,user):
        if message['request_receipt'] and not message['receipt']:
            ack=self.Message()
            ack['from']=message['to']
            ack['to']=message['from']
            ack['receipt']=message['id']
            ack.send()
        if message['cm_markable']:
            ack=self.Message()
            ack['from']=message['to']
            ack['to']=message['from']
            ack['cm_displayed']=message['id']
            ack.send()
        #TODO- put out admin commands
        #TODO- move control to AUser        
        if message['body']=="shutdown":
            self.shutdown(None)
            self.disconnect()
        elif message['body']=="status":
            message.reply()
            message['body']="Geocaching user %s"%(user.gcUser,)
            message.send()
            message['body']="Online :%s"%(user.mcConnection!=None,)
            message.send()
        elif message['body'].startswith("user "):
            user.gcUser=message['body'][len("user "):]        
        elif message['body'].startswith("pass "):
            user.gcPass=message['body'][len("pass "):]
            if user.online:
                user.setOnline()
        elif message['body']=="logout":
            user.logout()
        elif message['body']=="login":
            user.login()            
        elif message['body']=="poll":
            user.poll()
        elif message['body']=="ping":
            self.schedule("reply after wait",10,self.delayReply,(message['from'],))
            message.reply(body="pong").send()
            
    def delayReply(self,towards):
        message=self.Message()
        message['from']=self.config.bot
        message['to']=towards
        message['body']='After rethinking, i add...'
        message.send()


    def message_displayed(self,message):
        user=self.config.lookup(message['from'])
        if user==None:
            return
        user.messageDisplayed(message)

    def receipt_received(self,message):
        user=self.config.lookup(message['from'])
        if user==None:
            return
        if isBot(message):
            return
        
    def message (self,message):
        user=self.config.lookup(message['from'])
        if user==None:
            reply=self.Message()
            reply['from']=message['to']
            reply['id']=message['id']
            reply['to']=message['from']
            reply['error']['condition']='service-unavailable'
            reply['error']['type']='cancel'
            reply['error']['text']='Bitte registrieren'
            reply.send()
            return
        
        if isBot(message):
            self.botMessage(message,user)
            return
        
        if user.handleMessage(message):
            return
        
        reply=self.Message()
        reply['from']=message['to']
        reply['id']=message['id']
        reply['to']=message['from']
        reply['error']['condition']='service-unavailable'
        reply['error']['type']='cancel'
        reply['error']['text']='Other Error'
        reply.send()
        
    def loop():
        self.xm.Process(10)
        
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    config=Config()
    config.load()
    c=MyComponent(config.COMPONENT_NAME,config.COMPONENT_SECRET,config)
    config.load()
    config.setToXmpp(c)
    config.store()
    
    c.registerPlugin('xep_0030')
    c.registerPlugin('xep_0054')
    c.registerPlugin('xep_0086')
    c.registerPlugin('xep_0199')
    c.registerPlugin('xep_0184')
    c.registerPlugin('xep_0333')#Chat Markers
    c.registerPlugin('xep_0203')#Delayed Delivery
    c['xep_0184'].auto_ack=False
    c['xep_0184'].auto_request=False
    c.registerPlugin('xep_0071')
    
    if c.connect():
        c.process(block=True)
        print ("Done")
    else:
        print ("Unable to connect")
    
