#!/usr/bin/python

# Author: Goran Mandir


import sys, os, codecs, urllib, urlparse

from Utilities import removeTokenAndAddMissingSlash


class SiteReporter:
  def __init__(self, doHTMLValidation, checkLinkReference):
    self.validationReport   = {}
    self.brokenLinks        = {}
    self.allURLParents      = {}
    self.doHTMLValidation   = doHTMLValidation
    self.checkLinkReference = checkLinkReference
  

  def generateReport(self, filename):
    reportFile = codecs.open(filename, "w", "utf-8")
    reportFile.write("<!DOCTYPE HTML>\n<html><head>")
    reportFile.write("<meta charset='UTF-8'>\n")
    reportFile.write("<title>Site problem report "+filename+"</title>\n")
    #reportFile.write("<link rel='stylesheet' href='../bootstrap/css/bootstrap.min.css' type='text/css'>\n")
    reportFile.write("<link rel='stylesheet' href='http://twitter.github.com/bootstrap/assets/css/bootstrap.css' type='text/css'>\n")
    reportFile.write("<script type='text/javascript' src='https://ajax.googleapis.com/ajax/libs/jquery/1.8.2/jquery.min.js'></script>\n")
    #reportFile.write("<script type='text/javascript' src='../bootstrap/js/bootstrap.min.js'></script>\n")
    reportFile.write("<script type='text/javascript' src='http://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/2.1.1/bootstrap.min.js'></script>\n")
    reportFile.write("<script>"+self.jsContent()+"</script>")
    reportFile.write("</head><body>\n")
    reportFile.write("<div style='width: 1000px; margin-top: 50px; margin-left: 150px;'>")
    reportFile.write(self.htmlTabs())
    reportFile.write("<div class='tab-content'>")
    
    self.writeValidationResultsToReportFile(reportFile, "error", self.mergeReports("error"))
    self.writeValidationResultsToReportFile(reportFile, "warning", self.mergeReports("warning"))
    self.writeBrokenLinksToReportFile(reportFile)
    self.writeBrokenReferencesToReportFile(reportFile)
    self.writeValidatedLinksToReportFile(reportFile)
    
    reportFile.write("</div></div></body></html>\n")
    reportFile.close()
  
  
  def htmlTabs(self):
    # Tabs 
    return """<ul id='menuTabs' class='nav nav-tabs'>
                <li class='active'><a href='.errorList' data-toggle='tab'>Errors</a></li>
                <li><a href='.warningList' data-toggle='tab'>Warnings</a></li>
                <li><a href='.brokenLinkList' data-toggle='tab'>Broken Links</a></li>
                <li><a href='.pageReferenceList' data-toggle='tab'>Page References</a></li>
                <li><a href='.validatedLinksList' data-toggle='tab'>Validated Links</a></li>
              </ul>
"""
  
  
  def getRowBeginHTML(self, reportType, fontIcon):
    rowBeginHTML = u"<tr class='"+reportType+u"'><td>"+\
                   u"<i class='"+fontIcon+u"'></i> "
    
    return rowBeginHTML
  
  
  def mergeReports(self, reportType):
    allURLsPerError         = {}
    allURLsAndErrors        = {}
    
    for url, report in self.validationReport.iteritems():
      if (reportType == "error"):
        report = report['errors']
      elif (reportType == "warning"):
        report = report['warnings']
      
      for message in report:
        msg = (message['line']+
               message['col']+
               message['message'])
        
        if (msg not in allURLsPerError):
          allURLsPerError[msg] = {'urls'   : [url],
                                  'msgData': message}
        else:
          allURLsPerError[msg]['urls'].append(url)
    
    for  msg, urlsAndError in allURLsPerError.iteritems():
      urlsAndError['urls'].sort()

      urlJoin = "-".join(urlsAndError['urls'])

      if (urlJoin not in allURLsAndErrors):
        allURLsAndErrors[urlJoin] = urlsAndError
        allURLsAndErrors[urlJoin]['msgData'] = [allURLsAndErrors[urlJoin]['msgData']]
      else:
        allURLsAndErrors[urlJoin]['msgData'].append(urlsAndError['msgData'])
    
    return allURLsAndErrors
  
  
  def writeValidationResultsToReportFile(self, reportFile, reportType, mergedReports):
    if (reportType == "error"):
      tabClass = "in active errorList"
    elif (reportType == "warning"):
      tabClass = "warningList"
    else:
      raise Exception("Incorrect report type defined, only 'error' or 'warning' is allowed")
    
    reportFile.write("<div class='tab-pane fade "+tabClass+"' style='margin-top: 20px;'>\n")
    
    if (self.doHTMLValidation):
      haveWrittenReport = False
      
      for url, mergedReport in mergedReports.iteritems():
        if (len(mergedReport) > 0):
          haveWrittenReport = True
          
          self.writeReportsToReportFile(reportFile, reportType, mergedReport)
      
      if (haveWrittenReport == False):
        reportFile.write("<table class='table table-condensed'>\n")
        reportFile.write(self.getRowBeginHTML("info", "icon-info-sign")+
                         "There is nothing to report!</td></tr></table>")
    else:
      reportFile.write("<table class='table table-condensed'>\n")
      reportFile.write(self.getRowBeginHTML("info", "icon-minus-sign")+
                       "Page validation has been switched off for this test!</td></tr></table>")
    
    reportFile.write("</div>\n")
  
  
  def writeReportsToReportFile(self, reportFile, reportType, mergedReport):
    if (reportType == "error"):
      fontIcon = "icon-exclamation-sign"
    elif (reportType == "warning"):
      fontIcon = "icon-warning-sign"
    else:
      raise Exception("Incorrect report type defined, only 'error' or 'warning' is allowed")
    
    if (type(mergedReport) is dict and
        len(mergedReport) > 0):
      for url in mergedReport['urls']:
        reportFile.write("<h4><a href='"+url+"'>"+url+"</a></h4>")

      reportFile.write("<table class='table table-condensed'>\n")
      
      for message in mergedReport['msgData']:
        reportFile.write(self.getRowBeginHTML(reportType, fontIcon)+
                         u"Line "+message['line']+u", "+
                         u"Column "+message['col']+u": "+
                         message['message']+u"</td></tr>\n"+
                         u"<tr class='"+reportType+u"'><td>"+
                         message['source']+u"</td></tr>\n")
      
      reportFile.write("</table>\n")

  
  def writeBrokenLinksToReportFile(self, reportFile):
    reportFile.write("<div class='tab-pane fade brokenLinkList'>\n")
    reportFile.write("<table class='table table-striped'>\n")
    
    if (len(self.brokenLinks) > 0 and
        type(self.brokenLinks) is dict):
      reportFile.write("<thead><tr><th>Broken URL</th><th>Occurences</th></tr></thead><tbody>")
      
      for url, parentURLs in self.brokenLinks.iteritems():
        reportFile.write(self.getRowBeginHTML("error", "icon-remove-sign")+
                         url+"</td><td><ul>\n")
        
        parentURLs.sort()
        
        for parentURL in parentURLs:
          reportFile.write("<li><a href='"+parentURL+"'>"+parentURL+"</a></li>")
        
        reportFile.write("</ul></td></tr>\n")
      
      reportFile.write("</tbody>")
    else:
      reportFile.write(self.getRowBeginHTML("info", "icon-info-sign")+
                       "There are no broken links registered.</td></tr>\n")
      
    reportFile.write("</table>\n")
    reportFile.write("</div>\n\n")
  
  
  def getDuplicateReferences(self):
    duplicateReferences = {}
    
    for url, parentURLs in self.allURLParents.iteritems():
      urlParts = urlparse.urlsplit(url)
      
      # change the function link -> websiteChecker -> removeTokenAndAddMissingSlash()
      if (len(urlParts.query) > 1):
        splitURLPath = urlParts.path.lstrip('/').split('/', 2)
      else:
        splitURLPath = urlParts.path.strip('/').split('/', 2)
      
      if (len(urlParts.query) > 0):
        query = u"?"+urlParts.query
      else:
        query = u""
      
      if (len(splitURLPath) > 2):
        if (splitURLPath[1] == "base" or
            splitURLPath[1] == "project"):
          continue
        
        languageAndPageID     = "/"+splitURLPath[0]+"/"+splitURLPath[1]
        remainingPathAndQuery = "/"+splitURLPath[2]+query
      elif (len(splitURLPath) > 1):
        if (str(splitURLPath[1]).isdigit()):
          languageAndPageID     = "/"+splitURLPath[0]+"/"+splitURLPath[1]
          remainingPathAndQuery = "/"+query
        elif (not str(splitURLPath[1]).isdigit()):
          languageAndPageID     = "/"+splitURLPath[0]
          remainingPathAndQuery = "/"+splitURLPath[1]+"/"+query
      else:
        languageAndPageID     = "/"+splitURLPath[0]
        remainingPathAndQuery = "/"+query
      
      if (languageAndPageID not in duplicateReferences):
        duplicateReferences[languageAndPageID] = {"urlRemains": {remainingPathAndQuery: []}}
      elif (remainingPathAndQuery not in duplicateReferences[languageAndPageID]['urlRemains']):
        duplicateReferences[languageAndPageID]['urlRemains'][remainingPathAndQuery] = []
      
      for parentURL in parentURLs:
        if (parentURL not in duplicateReferences[languageAndPageID]['urlRemains'][remainingPathAndQuery]):
          duplicateReferences[languageAndPageID]['urlRemains'][remainingPathAndQuery].append(parentURL)
    
    # Remove any reference that has no duplicate references.
    for languageAndPageID in duplicateReferences.keys():
      if (len(duplicateReferences[languageAndPageID]['urlRemains']) < 2):
        del duplicateReferences[languageAndPageID]
    
    return duplicateReferences
  
  
  def writeBrokenReferencesToReportFile(self, reportFile):
    reportFile.write("<div class='tab-pane fade pageReferenceList'>\n")
    reportFile.write("<table class='table table-condensed'>\n")
    
    if (self.checkLinkReference):  
      duplicateReferences = self.getDuplicateReferences()
      
      if (len(duplicateReferences) > 0):
        for languageAndPageID, refPageItem in duplicateReferences.iteritems():
          reportFile.write(self.getRowBeginHTML("error", "icon-flag")+"\n"+languageAndPageID+"</td><td>Ocurrences</td></tr>\n")
          
          for remainingPathAndQuery in refPageItem['urlRemains']:
            reportFile.write(self.getRowBeginHTML("", ""))
            
            reportFile.write(remainingPathAndQuery)
            
            reportFile.write("</td><td><ul>")
            refPageParent = refPageItem['urlRemains'][remainingPathAndQuery]
            refPageParent.sort()
            
            for parentURL in refPageParent:
              reportFile.write("<li><a href='"+parentURL+"'>"+parentURL+"</a></li>")
            
            reportFile.write("</ul></td>")
          
          reportFile.write("</tr>")
      else:
        reportFile.write(self.getRowBeginHTML("info", "icon-minus-sign")+
                         "There are no broken reference links registered!</td></tr>")
    else:
      reportFile.write(self.getRowBeginHTML("info", "icon-minus-sign")+
                       "Checking link references has been switched off for this test!</td></tr>")
    
    reportFile.write("</table>\n")
    reportFile.write("</div>\n\n")

  
  def writeValidatedLinksToReportFile(self, reportFile):
    reportFile.write("<div class='tab-pane fade validatedLinksList'>\n")
    reportFile.write("<table class='table table-condensed'>\n")
    reportFile.write("<thead><tr><th>Validated links</th><th>Request time</th></tr></thead><tbody>")
    
    urls = self.validationReport.keys()
    urls.sort()
    
    for url in urls:
      reportFile.write(self.getRowBeginHTML("info", "icon-info-sign"))
      reportFile.write("<a href='"+url+"'>"+url+"</a>")
      reportFile.write("</td><td>")
      reportFile.write("( "+str(round(self.validationReport[url]['time'], 3))+" s )")
      reportFile.write("</td></tr>\n")
    
    reportFile.write("</table>\n")
    reportFile.write("</div>\n\n")
  
  
  def jsContent(self):
    # Script for htmlTabs functionality
    return """
$(document).ready(function()
{
  $("#menuTabs a[href='.errorList']").tab('show');
  
  $('#menuTabs a').click(function(e)
  {
    e.preventDefault();
    
    $(this).tab('show');
  });
});
"""


  def addValidationMessageToValidationReport(self, currentURL, errors, warnings, time):
    self.validationReport[currentURL] = {"errors"   : errors,
                                         "warnings" : warnings,
                                         "time"     : time}
  
  
  def addLinkToBrokenLinks(self, currentURL, parentURL):
    if (currentURL not in self.brokenLinks):
      self.brokenLinks[currentURL] = [parentURL]
    elif (parentURL not in self.brokenLinks[currentURL]):
      self.brokenLinks[currentURL].append(parentURL)
    
  
  def isURLInBrokenLinks(self, currentURL):
    return (currentURL in self.brokenLinks)
  
  
  def addLinkToAllURLParents(self, currentURL, parentURL):
    if (currentURL not in self.allURLParents):
      self.allURLParents[currentURL] = [parentURL]
    elif (parentURL not in self.allURLParents[currentURL]):
      self.allURLParents[currentURL].append(parentURL)
      
  
  def isURLInAllURLParents(self, currentURL):
    return (currentURL in self.allURLParents)