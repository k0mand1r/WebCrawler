#!/usr/bin/python

# Author: Goran Mandir

import time, sys, urlparse, urllib2, httplib, threading

import Utilities

from py_w3c.validators.html.validator import HTMLValidator
from py_w3c.exceptions import ValidationFault

# This management thread is to insure
# that all jobs are set to 'done' if no threads
# are left to handle the jobs. This can happen
# if all threads have raised exceptions which
# causes the queue.join() to wait forever for
# the jobs to finish, since no threads are left
# to finish the jobs.
class ThreadManagementThread(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    
    self.threadData   = {}
    self.threadDataID = 0
    self.doExit       = False


  def run(self):
    while True:
      if self.doExit:
        sys.exit(0)
      
      for threadDataID, threadDataItem in self.threadData.iteritems():
        if (len(threadDataItem['exceptions']) > 0):
          while (not threadDataItem['queue'].empty()):
            threadDataItem['queue'].get()
            
            threadDataItem['queue'].task_done()
      
      time.sleep(.01)
  
  
  def registerThreads(self, threads, queue, exceptions):
    self.threadData[self.threadDataID] = {'threads'   : threads,
                                          'queue'     : queue,
                                          'exceptions': exceptions}
    
    self.threadDataID += 1
    
    return (self.threadDataID - 1)
  
  
  def unregisterThreads(self, threadDataID):
    if (threadDataID in self.threadData):
      del self.threadData[threadDataID]
  
  
  def exit(self):
    self.doExit = True


class RequestPageThread(threading.Thread):
  def __init__(self, queue, jobsOutput, verboseOutput, exceptions):
    threading.Thread.__init__(self)
    self.queue         = queue
    self.jobsOutput    = jobsOutput
    self.cookie        = ""
    self.verboseOutput = verboseOutput
    self.exceptions    = exceptions
  
  
  def run(self):
    while True:
      try:
        job = self.queue.get()
        
        if ((type(job) == str or
             type(job) == unicode) and
            job == "die"):
          self.queue.task_done()
          
          sys.exit(0)
        
        startRequestTime = time.time()
        requestOutput    = self.requestPage(job['currentURL'])
        elapsedTime      = time.time() - startRequestTime
        
        self.jobsOutput.append({'requestOutput': requestOutput,
                                'elapsedTime'  : elapsedTime,
                                'currentURL'   : job['currentURL'],
                                'parentURL'    : job['parentURL']})
        
        self.queue.task_done()
      except Exception:
        self.exceptions.append(sys.exc_info())
        
        self.queue.task_done()
        
        sys.exit(0)


  def requestPage(self, currentURL):
    try:
      urlRequest = urllib2.Request(currentURL)
      
      if (len(self.cookie) > 0):
        urlRequest.add_header('Cookie', self.cookie)
      
      if (self.verboseOutput):
        print "  ["+self.getName()+"] "+currentURL
      
      requestOutput = urllib2.urlopen(urlRequest, timeout = 15)
      
      cookie = Utilities.getCookie(requestOutput)
      
      if (len(cookie) > 0):
        self.cookie = cookie
      
      return requestOutput
    except urllib2.URLError:
      if (self.verboseOutput):
        sys.stderr.write("  This URL " + currentURL + " can not be found.\n"+
                         "  It will be registered and the program will continue.\n\n")
      
      return False
 

class HTMLValidationThread(threading.Thread):
  def __init__(self, validationQueue, siteReporter, verboseOutput, exceptions):
    threading.Thread.__init__(self)
    self.queue         = validationQueue
    self.siteReporter  = siteReporter
    self.verboseOutput = verboseOutput
    self.exceptions    = exceptions
    self.validatorURL  = "http://validator.forion.com/check"
    self.htmlValidator = HTMLValidator(validator_url=self.validatorURL, charset="UTF-8")
  

  def run(self):
    while True:
      try:
        job = self.queue.get()
        
        if ((type(job) == str or
            type(job) == unicode) and
            job == "die"):
          self.queue.task_done()
          
          sys.exit(0)
        
        try:
          if (self.verboseOutput):
            print "  ["+self.getName()+"] "+job['currentURL']
          
          self.htmlValidator.validate_fragment(job['html'])
          
          self.siteReporter.addValidationMessageToValidationReport(job['currentURL'],
                                                                   self.htmlValidator.errors,
                                                                   self.htmlValidator.warnings,
                                                                   job['time'])
          self.queue.task_done()
        except ValidationFault, errorMsg:
          self.siteReporter.addValidationMessageToValidationReport(job['currentURL'],
                                                                   errorMsg,
                                                                   "",
                                                                   "")
          
          self.queue.task_done()
      except Exception:
        self.exceptions.append(sys.exc_info())
        
        self.queue.task_done()
        
        sys.exit(0)



class ImageLinkThread(threading.Thread):
  def __init__(self, queue, siteReporter, checkedLinks, verboseOutput, exceptions, mainSiteURL):
    threading.Thread.__init__(self)
    self.queue         = queue
    self.verboseOutput = verboseOutput
    self.siteReporter  = siteReporter
    self.exceptions    = exceptions
    self.mainSiteURL   = mainSiteURL
    self.checkedLinks  = checkedLinks
  
  
  def run(self):
    while True:
      try:
        job = self.queue.get()
        
        if ((type(job) == str or
             type(job) == unicode) and
            job == "die"):
          self.queue.task_done()
          
          sys.exit(0)
        
        imgParts = urlparse.urlsplit(job['imgURL'])
        
        if (len(imgParts.scheme) > 0 and
            len(imgParts.netloc) > 0 and
            len(imgParts.path) > 0):
          # IMG link is normal, don't do anything
          imgLink = job['imgURL']
        elif (len(imgParts.path) > 0 and
              imgParts.path[0] != "/"):
          # IMG link is relative, add domain name + img link
          if (job['parentURL'].endswith("/")):
            imgLink = job['parentURL'] + job['imgURL']
          else:
            imgLink = job['parentURL'] + "/" + job['imgURL']
        elif (len(imgParts.path) > 0 and
              imgParts.path[0] == "/"):
          # IMG link is absolute, add the domain name + img link
          imgLink = self.mainSiteURL + job['imgURL']
        
        try:
          if (imgLink not in self.checkedLinks):
            if (self.verboseOutput):
              print "  ["+self.getName()+"] "+job['imgURL']
            
            self.checkedLinks[imgLink] = job['parentURL']
            
            image = urllib2.urlopen(imgLink, timeout = 15)
            if (not image):
              self.siteReporter.addLinkToBrokenLinks(imgLink, job['parentURL'])
          elif (self.siteReporter.isURLInBrokenLinks(imgLink)):
            self.siteReporter.addLinkToBrokenLinks(imgLink, job['parentURL'])
        except (urllib2.URLError, ValueError, httplib.InvalidURL):
          self.siteReporter.addLinkToBrokenLinks(imgLink, job['parentURL'])
        
        self.queue.task_done()
      except Exception:
        self.exceptions.append(sys.exc_info())
        
        self.queue.task_done()
        
        sys.exit(0)


class ExternalLinkThread(threading.Thread):
  def __init__(self, queue, siteReporter, checkedLinks, verboseOutput, exceptions):
    threading.Thread.__init__(self)
    
    self.queue         = queue
    self.siteReporter  = siteReporter
    self.verboseOutput = verboseOutput
    self.exceptions    = exceptions
    self.checkedLinks  = checkedLinks
  
  
  def run(self):
    while True:
      # The check for broken external links
      try:
        job = self.queue.get()
        
        if ((type(job) == str or
             type(job) == unicode) and
            job == "die"):
          self.queue.task_done()
          
          sys.exit(0)
        
        try:
          if (job['urlToCheck'] not in self.checkedLinks):
            if (self.verboseOutput):
              print "  ["+self.getName()+"] "+job['urlToCheck']
            
            # Add user agent to HTTP-headers.
            # In rare cases this is needed to prevent getting a 403-error.
            request = urllib2.Request(job['urlToCheck'])
            request.add_header('User-agent', 'urllib2')
            
            self.checkedLinks[job['urlToCheck']] = job['parentURL']
            
            tmp = urllib2.urlopen(request)
          elif (self.siteReporter.isURLInBrokenLinks(job['urlToCheck'])):
            self.siteReporter.addLinkToBrokenLinks(job['urlToCheck'], job['parentURL'])
        except (urllib2.URLError, ValueError, httplib.InvalidURL):
          self.siteReporter.addLinkToBrokenLinks(job['urlToCheck'], job['parentURL'])
        
        self.queue.task_done()
      except Exception:
        self.exceptions.append(sys.exc_info())
        
        self.queue.task_done()
        
        sys.exit(0)