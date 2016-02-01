#!/usr/bin/python

# Author: Goran Mandir


import urllib, urlparse, re


def removeTokenAndAddMissingSlash(url):
  urlElement = urlparse.urlsplit(url)
  urlPathSplit = urlElement.path.lstrip('/').split('/', 2)
  
  if (len(urlElement.scheme) > 0 and
      urlElement.scheme != "http" and
      urlElement.scheme != "https"):
    return url
  
  if (len(urlPathSplit) > 1 and
      ("base" == urlPathSplit[1] or
       "project" == urlPathSplit[1])):
    urlElementPath = urlElement.path
  elif (len(urlPathSplit) > 0 and
        len(urlElement.query) == 0 and
        not urlElement.path.endswith('/')):
    urlElementPath = urlElement.path + "/"
  else:
    urlElementPath = urlElement.path
  
  # remove t (or token) from GET part of URL
  parsedQuery = urlparse.parse_qs(urlElement.query)
  
  if ("t" in parsedQuery):
    del parsedQuery['t']
  
  if ("v" in parsedQuery):
    del parsedQuery['v']
  
  encodedQuery = urllib.urlencode(parsedQuery, True)
  
  if (len(encodedQuery) > 0 and
      len(urlElement.scheme) > 0 and
      len(urlElement.netloc) > 0):
    encodedQuery = "?"+encodedQuery
    url = urlElement.scheme + "://" + urlElement.netloc + urlElementPath + encodedQuery
  elif (len(encodedQuery) == 0 and
        len(urlElement.netloc) > 0):
    url = urlElement.scheme + "://" + urlElement.netloc + urlElementPath
  else:
    url = urlElementPath
    
  return url


def getCookie(requestOutput):
    cookie = ""
    
    for httpHeader in requestOutput.info():
      if (httpHeader == "set-cookie"):
        cookie = requestOutput.info()[httpHeader]
        
        break
    
    return cookie
  

def getContentType(requestOutput):
  contentType = ""
  
  for httpHeader in requestOutput.info():
    if (httpHeader == "content-type"):
      contentType  = requestOutput.info()[httpHeader]
      
      break
    
  return contentType
