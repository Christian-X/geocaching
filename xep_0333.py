from sleekxmpp.xmlstream.stanzabase import ElementBase, ET
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.plugins.base import BasePlugin, register_plugin
from sleekxmpp.stanza import Message

class ChatMarker(ElementBase):
    namespace='urn:xmpp:chat-markers:0'
    
    def setup(self,xml=None):
        self.xml=ET.Element('')
        return True

class Markable(ChatMarker):
    name='markable'
    plugin_attrib='cm_markable'
    interfaces=set(('cm_markable',))
    sub_interfaces= interfaces
    is_extension= True
    
    def set_cm_markable(self,val):
        self.del_cm_markable()
        if val:
            parent=self.parent()
            parent._set_sub_text("{%s}markable"%self.namespace,keep=True)
            if not parent['id']:
                if parent.stream:
                    parent['id']=parent.stream.new_id()
    def get_cm_markable(self):
        parent=self.parent()
        if parent.find("{%s}markable"%self.namespace) is not None:
            return True
        else:
            return False
    
    def del_cm_markable(self):
        self.parent()._del_sub("{%s]markable"%self.namespace)

class Received(ChatMarker):
    name="received"
    plugin_attrib='cm_received'
    interfaces=set(('cm_received',))
    sub_interfaces=interfaces
    is_extension=True
    def set_cm_received(self,value):
        self.del_cm_received()
        if value:
            parent=self.parent()
            xml=ET.Element("{%s}received"%self.namespace)
            xml.attrib['id']=value
            parent.append(xml)
    def get_cm_received(self):
        parent=self.parent()
        xml=parent.find("{%s}received"%self.namespace)
        if xml is not None:
            return xml.attrib.get('id','')
        return ''
    def del_cm_received(self):
        self.parent()._del_sub("{%s}received"%self.namespace)
        

class Displayed(ChatMarker):
    name="displayed"
    plugin_attrib='cm_displayed'
    interfaces=set(('cm_displayed',))
    sub_interfaces=interfaces
    is_extension=True
    def set_cm_displayed(self,value):
        self.del_cm_displayed()
        if value:
            parent=self.parent()
            xml=ET.Element("{%s}displayed"%self.namespace)
            xml.attrib['id']=value
            parent.append(xml)
    def get_cm_displayed(self):
        parent=self.parent()
        xml=parent.find("{%s}displayed"%self.namespace)
        if xml is not None:
            return xml.attrib.get('id','')
        return ''
    def del_cm_displayed(self):
        self.parent()._del_sub("{%s}displayed"%self.namespace)
        
    

class XEP_0333(BasePlugin):
    
    """
    XEP-0333 Chat Markers
    """
    
    name  = 'xep_0333'
    description = 'XEP-0333: Chat Markers'
    dependencies = set(['xep_0030'])
    def plugin_init(self):
        register_stanza_plugin(Message,Markable)
        register_stanza_plugin(Message,Displayed)
        register_stanza_plugin(Message,Received)
        
register_plugin(XEP_0333)
