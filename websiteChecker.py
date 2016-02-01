#!/usr/bin/python

# Author: Goran Mandir

# Output een sitemap.xml van een website
# Link rapport (links - broken / external / ok, images - broken)
# Rapport over alle broken links + broken images (alle 404 errors)

import urllib, urllib2, httplib, sys, os, re, time, datetime
import errno, argparse, urlparse, py_w3c
import Queue, threading

import Utilities, Threader

from HTMLParser import HTMLParser
from SitemapGenerator import SitemapGenerator
from SiteReporter import SiteReporter



# grabs all links and images from the html and puts them in their own list
class HTMLParseRules(HTMLParser):
  def __init__(self):
    HTMLParser.__init__(self)
    
    self.cleanCurrentData()
  
  
  def cleanCurrentData(self):
    self.urls    = []
    self.imgURLs = []
  
  
  def handle_starttag(self, tag, attrs):
    # store all A tags
    if (tag == "a" and
        len(attrs) > 0):
      for attr in attrs:
        if (attr[0] == "href"):
          if (not attr[1].startswith("mailto:")):
            self.urls.append(attr[1])
            break
    # store all IMG tags      
    elif (tag == "img" and
          len(attrs) > 0):
      for attr in attrs:
        if (attr[0] == "src"):
          self.imgURLs.append(attr[1])
          break
  
  
  def getAllURLs(self):
    return self.urls
  
  
  def getAllImgURLs(self):
    return self.imgURLs


class RetrieveLinks():
  def __init__(self, siteURL, doHTMLValidation, verboseOutput, checkLinkReference, checkForBrokenImages, robotsAndFavicon):
    self.linksToBeChecked       = {}
    self.checkedLinks           = {}
    self.uncheckedExternalLinks = []
    self.doHTMLValidation       = doHTMLValidation
    self.checkLinkReference     = checkLinkReference
    self.checkForBrokenImages   = checkForBrokenImages
    self.robotsAndFavicon       = robotsAndFavicon
    self.siteURL                = siteURL
    self.siteURLParts           = urlparse.urlsplit(siteURL)
    self.sitemap                = SitemapGenerator()
    self.verboseOutput          = verboseOutput
    self.siteReporter           = SiteReporter(self.doHTMLValidation, self.checkLinkReference)
    self.threadManager          = None

  
  def run(self):
    parseHTMLPage         = HTMLParseRules()
    pathname              = "reports/"+self.siteURLParts.netloc
    imgsURLsToCheck       = []
    validationDataToCheck = []
    
    startTime = time.time()
    
    # Make a new directory if it doesn't exist
    # Else throw all error's except for when the directory already exists (errno.EEXIST)
    try:
      os.makedirs(pathname)
    except OSError as exception:
      if exception.errno != errno.EEXIST:
        raise
    
    realSiteURL = self.siteURL
    
    try:
      requestOutput = urllib2.urlopen(self.siteURL)
      
      self.sitemap.setHomePage(requestOutput.geturl())
      
      realSiteURL           = requestOutput.geturl()
      self.siteURLParts     = urlparse.urlsplit(realSiteURL)
      self.linksToBeChecked[realSiteURL] = None
    except urllib2.URLError:
      sys.stderr.write("Unable to connect to '"+self.siteURL+"'\n")
      sys.exit(0)
    
    self.threadManager = Threader.ThreadManagementThread()
    self.threadManager.start()
    
    # Create queue and threads for uber speed page requests.
    linksToBeCheckedQueue = Queue.Queue()
    jobsOutput            = []
    requestPageThreads    = []
    requestPageExceptions = []
    
    for i in range(5):
      thread = Threader.RequestPageThread(linksToBeCheckedQueue, jobsOutput, self.verboseOutput, requestPageExceptions)
      thread.start()
      
      requestPageThreads.append(thread)
    
    self.threadManager.registerThreads(requestPageThreads, linksToBeCheckedQueue, requestPageExceptions)
    
    if (self.robotsAndFavicon):
      if (self.checkForRobots(self.siteURL)):
        if (self.verboseOutput):
          print "Robots.txt is present"
      else:
        if (self.verboseOutput):
          print "Check if robots.txt is present"
      
      if (self.checkForFavicon(self.siteURL)):
        if (self.verboseOutput):
          print "Favicon.ico is present"
      else:
        if (self.verboseOutput):
          print "Check if favicon.ico is present"
    else:
      if (self.verboseOutput):
        print "Checking for robots.txt and favicon.ico has been switched off for this test!"
    
    # Run each link through the HTMLParser and HTMLvalidator
    while (len(self.linksToBeChecked) > 0):
      jobsOutput[:] = []

      if (self.verboseOutput):
        print "Checking URLs ..."
      
      while (len(self.linksToBeChecked) > 0):
        currentURL, parentURL = self.linksToBeChecked.popitem()
          
        if (currentURL not in self.checkedLinks):
          linksToBeCheckedQueue.put({'currentURL': currentURL,
                                     'parentURL' : parentURL})
      
      linksToBeCheckedQueue.join()
      
      if (self.verboseOutput):
        print "Done threading!\n"
      
      if (len(requestPageExceptions) > 0):
        self.threadManager.exit()
        raise requestPageExceptions[0][0], requestPageExceptions[0][1], requestPageExceptions[0][2]
      
      # lijst van alle jobs met HTML output van iedere job
      # for output in outputs:
      
      for jobOutput in jobsOutput:
        if (self.verboseOutput):
          print "  "+jobOutput['currentURL']+" ... ("+str(round(jobOutput['elapsedTime'], 3))+")"
        
        if (jobOutput['requestOutput'] == False or
            not hasattr(jobOutput['requestOutput'], "geturl")):
          self.siteReporter.addLinkToBrokenLinks(jobOutput['currentURL'], jobOutput['parentURL'])
          self.checkedLinks[jobOutput['currentURL']] = jobOutput['parentURL']
          
          continue
        elif (jobOutput['requestOutput'].geturl() != jobOutput['currentURL']):
          self.checkedLinks[jobOutput['currentURL']] = jobOutput['parentURL']
          
          jobOutput['currentURL'] = jobOutput['requestOutput'].geturl()
        
        if (jobOutput['currentURL'] in self.checkedLinks):
          # Happens if the site redirects us to a page that we've already done before.
          continue
        
        if ("text/html" not in Utilities.getContentType(jobOutput['requestOutput'])):
          #print "Request: " + str(requestOutput) + " Parent: ", parentURL, "\n"
          # The request file is not an HTML page, so we skip it.
          self.checkedLinks[jobOutput['currentURL']] = jobOutput['parentURL']
          
          continue
        
        # Set encoding for UTF-8 pages.
        encoding = jobOutput['requestOutput'].headers.getparam('charset')
        html     = jobOutput['requestOutput'].read().decode(encoding)
        
        parseHTMLPage.cleanCurrentData()
        parseHTMLPage.feed(html)
        parseHTMLPage.close()
        
        urlsInCurrentPage = parseHTMLPage.getAllURLs()
        imgsInCurrentPage = parseHTMLPage.getAllImgURLs()
        
        self.collectURLs(urlsInCurrentPage, jobOutput['currentURL'])
        
        self.sitemap.addURL(jobOutput['currentURL'], jobOutput['parentURL'])
        
        if (jobOutput['parentURL'] is None):
          parentURL = realSiteURL
        else:
          parentURL = jobOutput['parentURL']
        
        for imgURL in imgsInCurrentPage:
          imgsURLsToCheck.append({'imgURL'   : imgURL,
                                  'parentURL': parentURL})
        
        # Perform HTML validation
        if (self.doHTMLValidation):
          validationDataToCheck.append({'currentURL': jobOutput['currentURL'],
                                        'html'      : html,
                                        'time'      : jobOutput['elapsedTime']})
        
        # Print if a link has been checked.
        # Reference: def run() -> while -> try -> print
        #if (self.verboseOutput):
        #  print ""
          #print "  Parent: ", parentURL
          #print "Done checking "+jobOutput['currentURL']+"\n"
        
        self.checkedLinks[jobOutput['currentURL']] = jobOutput['parentURL']
      
      if (self.verboseOutput):
        print ""
      
      # End of while loop
    
    nrOfLivingThreads = 0
    for thread in requestPageThreads:
      if (thread.isAlive()):
        nrOfLivingThreads += 1
    
    for i in range(nrOfLivingThreads):
      linksToBeCheckedQueue.put('die')
    
    linksToBeCheckedQueue.join()
    
    # Process html validation in a thread-class
    if (self.doHTMLValidation):
      if (self.verboseOutput):
        print "Sending validation request for ..."
        
      self.executeValidation(validationDataToCheck)
        
      if (self.verboseOutput):
        print "Requests has been validated!\n"
    else:
      if (self.verboseOutput):
        print "Validating URLs has been switched off for this test!"
    
    # process external links in a thread-class
    if (self.verboseOutput):
      print "Checking external links ..."
    
    self.executeJobs(self.uncheckedExternalLinks, "externalLinks", 20)
    
    if (self.verboseOutput):
      print "Done checking external links!\n"
    
    # Process image links in a thread-class
    if (self.checkForBrokenImages):
      if (self.verboseOutput):
        print "Checking for broken image links ..."
        
      self.executeJobs(imgsURLsToCheck, "imageLinks")
      
      if (self.verboseOutput):
        print "Done checking for broken image links!\n "
    else:
      if (self.verboseOutput):
        print "Checking for broken image links has been switched off for this test!\n"
    
    self.threadManager.exit()
    
    currentDate = datetime.datetime.now()
    date = currentDate.strftime("%d-%m-%Y")
    self.siteReporter.generateReport(pathname+"/"+self.siteURLParts.netloc+"-problemReport-"+date+".html")
    
    self.sitemap.generateSitemap(pathname+"/"+self.siteURLParts.netloc+"-sitemap-"+date+".xml")
    
    if (self.verboseOutput):
      print str(time.time() - startTime)+" seconds!"
    
    if (self.verboseOutput):
      print "Check finished!"
  
  
  def collectURLs(self, urls, currentURL):
    for url in urls:
      urlParts       = urlparse.urlsplit(url)
      urlToBeChecked = None
      
      if (urlParts.netloc == self.siteURLParts.netloc):
        if (url not in self.linksToBeChecked and
            url not in self.checkedLinks):
          urlToBeChecked = Utilities.removeTokenAndAddMissingSlash(url)
      elif (urlParts.scheme == "" and
            urlParts.netloc == ""):
        if (len(urlParts.fragment) > 0):
          pass
        elif (urlParts.path == "" and
              len(urlParts.query) > 0):
          # Only a query part in the URL.
          urlToBeChecked = currentURL+urlParts.query
        elif (len(urlParts.path) > 0 and
              urlParts.path[0] == "/"):
          # Absolute URL to the URL we're now currently at.
          
          currentURLParts = urlparse.urlsplit(currentURL)
          
          urlParts = urlparse.urlsplit(Utilities.removeTokenAndAddMissingSlash(url))
          
          if (len(urlParts.query) > 0):
            query = u"?"+urlParts.query
          else:
            query = u""
          
          urlToBeChecked = currentURLParts.scheme+"://"+currentURLParts.netloc+urlParts.path+query
        elif (len(urlParts.path) > 0 and
              urlParts.path[0] != "/"):
          # Relative URL to the URL we're now currently at.
          
          urlParts = urlparse.urlsplit(Utilities.removeTokenAndAddMissingSlash(url))
          
          if (len(urlParts.query) > 0):
            query = u"?"+urlParts.query
          else:
            query = u""
          
          urlToBeChecked = currentURL + urlParts.path + query
      elif (urlParts.netloc != self.siteURLParts.netloc):
        self.uncheckedExternalLinks.append({'urlToCheck': url,
                                            'parentURL' : currentURL})
      elif (len(urlParts.fragment) > 0):
        continue
      
      if (type(urlToBeChecked) == unicode and
          urlToBeChecked not in self.checkedLinks and
          urlToBeChecked not in self.linksToBeChecked and
          currentURL != urlToBeChecked):
        self.linksToBeChecked[urlToBeChecked] = currentURL
        
        self.siteReporter.addLinkToAllURLParents(urlToBeChecked, currentURL)
      
      if (type(urlToBeChecked) == unicode and
          self.siteReporter.isURLInBrokenLinks(urlToBeChecked)):
        self.siteReporter.addLinkToBrokenLinks(urlToBeChecked, currentURL)
      elif (self.siteReporter.isURLInBrokenLinks(url)):
        self.siteReporter.addLinkToBrokenLinks(url, currentURL)
        
      if (type(urlToBeChecked) == unicode and
          self.siteReporter.isURLInAllURLParents(urlToBeChecked)):
        self.siteReporter.addLinkToAllURLParents(urlToBeChecked, currentURL)
      elif (self.siteReporter.isURLInAllURLParents(url)):
        self.siteReporter.addLinkToAllURLParents(url, currentURL)
      
      #print "-----------------------------------------------------\n"


  def executeJobs(self, jobs, jobType, nrOfThreads = 5):
    queue        = Queue.Queue()
    checkedLinks = {}
    exceptions   = []
    threads      = []
    
    for i in range(nrOfThreads):
      if (jobType == "imageLinks"):
        thread = Threader.ImageLinkThread(queue, self.siteReporter, checkedLinks, self.verboseOutput, exceptions, self.siteURL)
      elif (jobType == "externalLinks"):
        thread = Threader.ExternalLinkThread(queue, self.siteReporter, checkedLinks, self.verboseOutput, exceptions)
      
      thread.start()
      
      threads.append(thread)
    
    threadDataID = self.threadManager.registerThreads(threads, queue, exceptions)
    
    for job in jobs:
      queue.put(job)
    
    queue.join()
    
    nrOfLivingThreads = 0
    for thread in threads:
      if (thread.isAlive()):
        nrOfLivingThreads += 1
    
    for i in range(nrOfLivingThreads):
      queue.put('die')
    
    queue.join()
    
    if (len(exceptions) > 0):
      self.threadManager.exit()
      raise exceptions[0][0], exceptions[0][1], exceptions[0][2]
    else:
      self.threadManager.unregisterThreads(threadDataID)
  
  
  def executeValidation(self, jobs):
    queue      = Queue.Queue()
    exceptions = []
    threads    = []
    
    for i in range(5):
      thread = Threader.HTMLValidationThread(queue, self.siteReporter, self.verboseOutput, exceptions)
      thread.start()
      
      threads.append(thread)
    
    self.threadManager.registerThreads(threads, queue, exceptions)
    
    for job in jobs:
      queue.put(job)
    
    queue.join()
    
    nrOfLivingThreads = 0
    for thread in threads:
      if (thread.isAlive()):
        nrOfLivingThreads += 1
    
    for i in range(nrOfLivingThreads):
      queue.put('die')
    
    queue.join()
    
    if (len(exceptions) > 0):
      self.threadManager.exit()
      raise exceptions[0][0], exceptions[0][1], exceptions[0][2]

  
  # Check if robots.txt exists in the root directory
  def checkForRobots(self, siteURL):
    robots   = urllib2.urlopen(self.siteURLParts.scheme + "://" + self.siteURLParts.netloc + "/robots.txt")
    if (robots):
      return True
    else:
      pass
    
    
  # Check if favicon.ico exists in the root directory  
  def checkForFavicon(self, siteURL):
    favicon = urllib2.urlopen(self.siteURLParts.scheme + "://" + self.siteURLParts.netloc + "/favicon.ico")
    
    if (favicon):
      return True
    else:
      pass


def main():
  parser = argparse.ArgumentParser(description="Script that runs through a website at the given URL, to validate the HTML of all pages, generate a sitemap.xml, and report back any broken links, images, html errors and html warnings")
  parser.add_argument("-s", "--site-url"          , help="The URL of the website to be checked. Example: http://domain-name.com", dest="siteURL", required=True)
  parser.add_argument("-d", "--dont-validate-html", help="Do not validate the HTML of the retrieved pages", action="store_false", default=True  , dest="doHTMLValidation")
  parser.add_argument("-v", "--verbose"           , help="Give verbose output"                            , action="store_true" , default=False , dest="verboseOutput")
  parser.add_argument("-l", "--link-reference"    , help="Do not check the reference from links to pages" , action="store_false", default=True  , dest="checkLinkReference")
  parser.add_argument("-i", "--check-images"      , help="Do not check for broken images"                 , action="store_false", default=True  , dest="checkForBrokenImages")
  parser.add_argument("-r", "--check-robots-fav"  , help="Do not check if robots and favicon are present" , action="store_false", default=True  , dest="robotsAndFavicon")
  
  args = parser.parse_args()
  
  rl = RetrieveLinks(args.siteURL, args.doHTMLValidation, args.verboseOutput, args.checkLinkReference, args.checkForBrokenImages, args.robotsAndFavicon)
  rl.run()
  

if (__name__ == '__main__'):
  main()
  
