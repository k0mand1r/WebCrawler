#!/usr/bin/python

# Author: Goran Mandir


import urlparse, urllib, re
from math import floor

from Utilities import removeTokenAndAddMissingSlash


class SitemapGenerator():
  def __init__(self):
    self.sitemapLinks = {}
    self.homePage     = None
    
  
  def setHomePage(self, siteURL):
    self.homePage = removeTokenAndAddMissingSlash(siteURL)
  
  
  def getPriority(self, url):
    if (type(self.sitemapLinks[url]['priority']) is not float):
      self.sitemapLinks[url]['priority'] = self.getPriority(self.sitemapLinks[url]['parent']) / 2.0
      
    return self.sitemapLinks[url]['priority']
  
  
  def generateSitemap(self, filename):
    sitemapFileHdl = open(filename, "w")
    
    sitemapFileHdl.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    sitemapFileHdl.write("<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n")
    
    for url in self.sitemapLinks:
      priority = self.getPriority(url)
      flooredPriority = floor(priority*10) / 10
      if (flooredPriority < 0.1):
        flooredPriority = 0.1
      
      sitemapFileHdl.write("  <url>\n")
      sitemapFileHdl.write("    <loc>"+url+"</loc>\n")
      sitemapFileHdl.write("    <changefreq>daily</changefreq>\n")
      sitemapFileHdl.write("    <priority>"+str(flooredPriority)+"</priority>\n")
      sitemapFileHdl.write("  </url>\n")
    
    sitemapFileHdl.write("</urlset>\n")
    
    sitemapFileHdl.close()
  
  
  def addURL(self, url, parentURL):
    url = removeTokenAndAddMissingSlash(url)
    
    if (url is None):
      return
    
    if (type(parentURL) == str):
      parentURL = removeTokenAndAddMissingSlash(parentURL)
      
      if (parentURL is None):
        return
    
    if (url == self.homePage):
      if (url not in self.sitemapLinks):
        self.sitemapLinks[url] = {'parent'  : None,
                                  'priority': 1.0}
        #print "\n       added to sitemapLinks: " + url + "\n"
    else:
      if (url not in self.sitemapLinks):
        self.sitemapLinks[url] = {'parent'  : parentURL,
                                  'priority': None}
        #print "  added to sitemapLinks: " + url + "\n"