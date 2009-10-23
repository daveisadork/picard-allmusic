# -*- coding: utf-8 -*-

PLUGIN_NAME = u"AllMusic Genres"
PLUGIN_AUTHOR = u"Dave Hayes"
PLUGIN_DESCRIPTION = "Scrape AllMusic for Genre Tags"
PLUGIN_VERSION = "0.1"
PLUGIN_API_VERSIONS = ["0.9.0", "0.10"]

from PyQt4 import QtCore
from picard.metadata import register_album_metadata_processor
from difflib import get_close_matches
from BeautifulSoup import BeautifulSoup
import urllib
import urllib2
import sys
import re

def get_album_data(url, albumartist):
    print " * Requesting album page",
    try:
        html = urllib2.urlopen(url).read().replace("</scr'+'ipt>","</script>")
    except:
        print "[fail]"
    if albumartist == u"Various Artists":
        html = html.replace('<class="subtitle">Various Artists','<a href="" class="subtitle">Various Artists</a>')
    soup = BeautifulSoup(html)
    print "[ OK ]"
    return soup

def scrape_styles(soup):
    styles = []
    print " * Scraping styles:",
    try:
        for style in soup.find(text="Styles Listing").findNext('ul').findAll('a'):
            styles.append(style.contents[0].replace("/ ","/"))
        if styles == []:
            print "none"
            return
        for style in styles:
            if style != styles[0]:
                print "\b, " + style,
            else:
                print style,
        return styles
    except:
        print "[fail]"
        return

def album_search(albumartist, album):
    base_url = "http://allmusic.com/cg/amg.dll"
    arguments = {'P' : 'amg', 'opt1' : '2', 'sql' : album}
    try:
        url = urllib2.Request(base_url, urllib.urlencode(arguments))
    except:
        print "[fail]"
        return
    try:
        html = urllib2.urlopen(url).read().replace("</scr'+'ipt>","</script>")
    except:
        print "[fail]"
        return
    soup = BeautifulSoup(html)
    print "[ OK ]"
    return soup

def parse_results(soup, albumartist, album):
    results = []
    strings = []
    urls = []
    print " * Parsing search results",
    for listings in soup.find(id="results-table").findAll('tr', attrs={"class" : "visible"}):
        artist_string = listings.find(style="width:206px;word-wrap:break-word;").string
        album_string = listings.find(style="width:230px;word-wrap:break-word;").a.string
        album_url = listings.find(style="width:230px;word-wrap:break-word;").a["href"]
        search_string = artist_string + album_string
        results.append([artist_string, album_string, search_string, album_url])
    if results == []:
        print "[fail]"
        return
    print "[ OK ]"
    for records in results:
        strings.append(records[2])
        urls.append(records[3])
    search_string = albumartist + album
    print " * Looking for a close match:",
    match = get_close_matches(search_string, strings, 1, 0.6)
    if match == []:
        print "none"
        return
    for search in results:
        if match[0] == search[2].encode('utf-8'):
            print search[1] + " by " + search[0]
            return "http://allmusic.com" + search[3]

def cleanAlbumName(albumName):
    album = albumName
    _discnumber_re = re.compile(r"\s+\(disc (\d+)(?::\s+([^)]+))?\)")
    matches = _discnumber_re.search(album)
    if matches:
        album = album.replace(matches.group(0),'')
    _bonusdisc_re = re.compile(r"\s+\(bonus disc(?::\s+([^)]+))?\)")
    matches = _bonusdisc_re.search(album)
    if matches:
        album = album.replace(matches.group(0),'')
    return album

def allmusic_genre(album, metadata, release):
    sane_album = cleanAlbumName(metadata["album"])
    print " * Looking for " + sane_album + " by " + metadata["albumartist"]
    print " * Sending search request",
    search_results = album_search(metadata["albumartist"], sane_album)
    if search_results == None:
        return
    album_url = parse_results(search_results, metadata["albumartist"], sane_album)
    if album_url == None:
        return
    album_data = get_album_data(album_url, metadata["albumartist"])
    if album_data == None:
        return
    styles = scrape_styles(album_data)
    if styles == []:
        return
    metadata["genre"] = styles
    print '\n'

register_album_metadata_processor(allmusic_genre)
