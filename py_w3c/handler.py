#!/usr/bin/python
'''
Handler for W3C validation api response 
'''

from xml.sax import handler


class ValidatorHandler(handler.ContentHandler):
    def __init__(self):
        self.tags = {}
        self.doctype = ''
        self.charset = ''
        self.validity = ''
        self.errors = []
        self.warnings = []
        self.last_error = {}
        self.last_warning = {}
        self.errorcount = 0
        self.warningcount = 0
        self.fault_occured = False
        self.fault_message = ""

    def startElement(self, name, attrs):
        if ':' in name:
            namespace, localname = name.split(':')
        else:
            localname = name
        self.tags.update({'in_%s' % localname: True})

    def characters(self, content):
        if self.tags.get('in_doctype'):
            self.doctype = content
        if self.tags.get('in_charset'):
            self.charset = content
        if self.tags.get('in_validity'):
            self.validity = content

	if self.tags.get('in_Envelope') and self.tags.get('in_Body') and self.tags.get('in_Fault') and self.tags.get('in_errordetail'):
	    self.fault_occured = True
	    self.fault_message = "%s%s" % (self.fault_message, content)
	    
        if self.tags.get('in_errors') and self.tags.get('in_errorcount'):
            self.errorcount = int(content)
                        
        if self.tags.get('in_errorlist') and self.tags.get('in_error'):
            if self.tags.get('in_line'):
                self.last_error.update({'line': content})
            elif self.tags.get('in_col'):
                self.last_error.update({'col': content})
            elif self.tags.get('in_source'):
                self.last_error.update({'source': '%s%s' % (self.last_error.get('source', ''), content)})
            elif self.tags.get('in_explanation'):
                self.last_error.update({'explanation': '%s%s' % (self.last_error.get('explanation', ''), content)})
            elif self.tags.get('in_message'):
                self.last_error.update({'message': '%s%s' % (self.last_error.get('message', ''), content)})
            elif self.tags.get('in_messageid'):
                self.last_error.update({'messageid': content})

        if self.tags.get('in_warnings') and self.tags.get('in_warningcount'):
            self.warningcount = int(content)

        if self.tags.get('in_warninglist') and self.tags.get('in_warning'):
            if self.tags.get('in_line'):
                self.last_warning.update({'line': content})
            elif self.tags.get('in_col'):
                self.last_warning.update({'col': content})
            elif self.tags.get('in_source'):
                self.last_warning.update({'source': '%s%s' % (self.last_error.get('source', ''), content)})
            elif self.tags.get('in_explanation'):
                self.last_warning.update({'explanation': '%s%s' % (self.last_error.get('explanation', ''), content)})
            elif self.tags.get('in_message'):
                self.last_warning.update({'message': '%s%s' % (self.last_error.get('message', ''), content)})
            elif self.tags.get('in_messageid'):
                self.last_warning.update({'messageid': content})

    def endElement(self, name):
        if ':' in name:
            namespace, localname = name.split(':')
        else:
            localname = name
        self.tags.update({'in_%s' % localname: False})

        if localname == 'error':
            self.errors.append(self.last_error.copy())
            self.last_error = {}
