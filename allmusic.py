# -*- coding: utf-8 -*-

PLUGIN_NAME = u"AllMusic Genres"
PLUGIN_AUTHOR = u"Dave Hayes"
PLUGIN_DESCRIPTION = "Scrape AllMusic for Genre Tags"
PLUGIN_VERSION = "0.1"
PLUGIN_API_VERSIONS = ["0.9.0", "0.10"]

from PyQt4 import QtCore
from PyQt4.QtCore import QUrl
from picard.metadata import register_album_metadata_processor
import urllib,urllib2,sys
from BeautifulSoup import BeautifulSoup
from BeautifulSoup import NavigableString

def scrape_album(url):
    print url
    output = open("/home/dhayes/Desktop/output.txt","w")
    html = urllib2.urlopen(url).read().replace("</scr'+'ipt>","</script>")
    soup = BeautifulSoup(html)
    output.write(soup.prettify())
    try:
        for styles in soup.find(text="Styles Listing").findNext('ul').findAll('a'):
            print styles.contents[0]
    except AttributeError:
        print "Looks like the page is malformed or something"
        return
    
def album_search(albumartist, album):
    base_url = "http://allmusic.com"
    url = base_url + "/cg/amg.dll?P=amg&opt1=2&sql=" + urllib.quote(album)
    html = urllib2.urlopen(url).read().replace("</scr'+'ipt>","</script>")
    soup = BeautifulSoup(html)
    try:
        album_link = soup.find(id="albumsearchresults").find(text=albumartist).findNext('td').findNext('td').a
        print "Using album link titled " + album_link.string + " with url:"
        return base_url + album_link['href']
    except AttributeError:
        print "Couldn't find the right album, moving on"
        return
       
def allmusic_genre(album, metadata, release, try_list=None):
    #if metadata["albumartist"] == "Various Artists":
    #    return
    album_url = album_search(metadata["albumartist"],metadata["album"])
    if album_url:
        genres = scrape_album(album_url)
    return

register_album_metadata_processor(allmusic_genre)
