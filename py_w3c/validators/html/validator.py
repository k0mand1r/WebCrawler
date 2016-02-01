import urllib2
import urllib
import sys
import getopt

from xml.sax import parseString

from py_w3c.multipart import Multipart
from py_w3c.handler import ValidatorHandler
from py_w3c.exceptions import ValidationFault
from py_w3c import __version__

VALIDATOR_URL = 'http://validator.w3.org/check'


class HTMLValidator(object):
    def __init__(self, validator_url=VALIDATOR_URL, charset=None, doctype=None,
        verbose=False):
        self.validator_url = validator_url
        self.result = None
        self.uri = ''
        self.uploaded_file = ''
        self.output = 'soap12'
        self.charset = charset
        self.doctype = doctype
        self.errors = []
        self.warnings = []
        self.verbose = verbose

    def _validate(self, url, headers=None, post_data=None):
        ''' sends request to the validator, if post_data is not empty, sends POST request, otherwise sends GET request. 
        Returns True if validation occurs, otherwise otherwise raises exception '''
        if not headers:
            headers = {}
        req = urllib2.Request(url, headers=headers, data=post_data)
        resp = urllib2.urlopen(req)
        self._process_response(resp.read())
        return True

    def validate(self, uri):
        ''' validates by uri '''
        get_data = {'uri': uri, 'output': self.output}
        if self.charset:
            get_data['charset'] = self.charset
        if self.doctype:
            get_data['doctype'] = self.doctype
        get_data = urllib.urlencode(get_data)
        return self._validate(self.validator_url + '?' + get_data)

    def validate_file(self, filename_or_content, name='file'):
        ''' validates by filename or file content '''
        m = Multipart()
        m.field('output', self.output)
        if self.doctype:
            m.field('doctype', self.doctype)
        if self.charset:
            m.field('charset', self.charset)
        if isinstance(filename_or_content, str):
            with open(filename_or_content, "r") as w:
                content = w.read()
        elif isinstance(filename_or_content, file):
            content = filename_or_content.read()
        else:
            raise Exception("File name or file content only. Got %s instead" % type(filename_or_content))
        m.file('uploaded_file', name, content, {'Content-Type': 'text/html'})
        ct, body = m.get()
        return self._validate(self.validator_url, headers={'Content-Type': ct}, post_data=body)

    def validate_fragment(self, fragment):
        ''' validates by fragment. Full html fragment only. '''
        post_data = {'fragment': fragment.encode(self.charset), 'output': self.output}
        if self.doctype:
            post_data['doctype'] = self.doctype
        if self.charset:
            post_data['charset'] = self.charset
        
        post_data = urllib.urlencode(post_data)
        return self._validate(self.validator_url, post_data=post_data)

    def _process_response(self, response):
        val_handler = ValidatorHandler()
        parseString(response, val_handler)
        if val_handler.fault_occured:
            raise ValidationFault("Fault occurs. %s" % val_handler.fault_message + "\n")
        if self.verbose:
            print "Errors: %s" % len(self.errors)
            print "Warnings: %s" % len(self.warnings)
        self.result = val_handler
        self.warnings = val_handler.warnings
        self.errors = val_handler.errors

def main(argv=None):
    usage = "  Usage: \n    w3c_validator http://yourdomain.org"
    if argv is None:
        argv = sys.argv
    if len(argv) != 2:
        print usage
        sys.exit(2)
    if argv[1] in ("-v", "--version"):
        print __version__
        sys.exit(0)
    val = HTMLValidator(verbose=False)
    val.validate(argv[1])
    print "---warnings---(%s)" % len(val.warnings)
    for warning in val.warnings:
        print "line:%s; col:%s; message:%s" % (warning.get("line"), warning.get("col"), warning.get("message"))
    print "---errors---(%s)" % len(val.errors)
    for error in val.errors:
        print "line:%s; col:%s; message:%s" % (error.get("line"), error.get("col"), error.get("message"))
    sys.exit(0)

