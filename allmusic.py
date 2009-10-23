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

def parse_artist_search(search_results, albumartist):
    brackets = re.compile(r" \[.*]")
    results = []
    artists = []
    print " * Parsing artist search results",
    for listings in search_results.find(id="results-table").findAll('tr'):
        try:
            artist_string = listings.find(style="width:290px;word-wrap:break-word;").find('a').string#.encode('utf-8')
            artist_url = listings.find(style="width:290px;word-wrap:break-word;").find('a')['href']
            matches = brackets.search(artist_string)
            if matches:
                artist_string = artist_string.replace(matches.group(0),'')
            results.append([artist_string,artist_url])
            artists.append(artist_string)
        except:
            pass
    if results == []:
        print "[fail]"
        return
    print "[ OK ]"
    print " * Looking for a close match:",
    match = get_close_matches(albumartist, artists, 1, 0.85)
    if match == []:
        print "none"
        return
    print match[0]
    for search in results:
        if match[0].encode('utf-8') == search[0]:
            artist_data = get_artist_data("http://allmusic.com" + search[1])
            return artist_data
    return

def get_artist_data(artist_url):
    if artist_url == None:
        return
    print " * Requesting artist data",
    try:
        html = urllib2.urlopen(artist_url).read().replace("</scr'+'ipt>","</script>")
    except:
        print "[fail]"
        return
    artist_data = BeautifulSoup(html)
    print "[ OK ]"
    return artist_data

def artist_search(albumartist):
    print " * Sending artist search request",
    base_url = "http://allmusic.com/cg/amg.dll"
    arguments = {'P' : 'amg', 'opt1' : '1', 'sql' : albumartist}
    try:
        artist_search_url = urllib2.Request(base_url, urllib.urlencode(arguments))
    except:
        print "[fail]"
        return
    try:
        html = urllib2.urlopen(artist_search_url).read().replace("</scr'+'ipt>","</script>")
    except:
        print "[fail]"
        return
    artist_search_results = BeautifulSoup(html)
    if artist_search_results.html.head.title.string == "allmusic":
        print "[ OK ]"
        artist_data = parse_artist_search(artist_search_results, albumartist)
    else:
        print "[ OK ]"
        artist_data = artist_search_results
    if artist_data == None:
        return
    return artist_data

def get_album_data(album_url, albumartist):
    if album_url == None:
        return
    print " * Requesting album page",
    try:
        html = urllib2.urlopen(album_url).read().replace("</scr'+'ipt>","</script>")
    except:
        print "[fail]"
        return
    if albumartist == u"Various Artists":
        html = html.replace('<class="subtitle">Various Artists', '<a href="" class="subtitle">Various Artists</a>')
    album_data = BeautifulSoup(html)
    print "[ OK ]"
    return album_data

def album_search(albumartist, album):
    base_url = "http://allmusic.com/cg/amg.dll"
    arguments = {'P' : 'amg', 'opt1' : '2', 'sql' : album}
    print " * Sending album search request",
    try:
        album_search_url = urllib2.Request(base_url, urllib.urlencode(arguments))
    except:
        print "[fail]"
        return
    try:
        html = urllib2.urlopen(album_search_url).read().replace("</scr'+'ipt>","</script>")
    except:
        print "[fail]"
        return
    album_search_results = BeautifulSoup(html)
    print "[ OK ]"
    album_url = parse_album_search(album_search_results, albumartist, album)
    album_data = get_album_data(album_url, albumartist)
    return album_data

def parse_album_search(search_results, albumartist, album):
    results = []
    strings = []
    print " * Parsing album search results",
    for listings in search_results.find(id="results-table").findAll('tr', attrs={"class" : "visible"}):
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

def clean_album_name(album):
    discnumber = re.compile(r"\s+\(disc (\d+)(?::\s+([^)]+))?\)")
    matches = discnumber.search(album)
    if matches:
        album = album.replace(matches.group(0),'')
    bonusdisc = re.compile(r"\s+\(bonus disc(?::\s+([^)]+))?\)")
    matches = bonusdisc.search(album)
    if matches:
        album = album.replace(matches.group(0),'')
    return album

def scrape_styles(data):
    styles = []
    print " * Scraping styles:",
    try:
        for style in data.find(text="Genre Listing").findNext('ul').findAll('a'):
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
        print "none"
        return styles

def allmusic_genre(album, metadata, release):
    styles = []
    album = clean_album_name(metadata["album"])
    print " * Looking for " + album + " by " + metadata["albumartist"]
    data = album_search(metadata["albumartist"], album)
    if data != None:
        styles = scrape_styles(data)
    if styles == [] and metadata["albumartist"] != "Various Artists":
        data = artist_search(metadata["albumartist"])
        if data != None:
            styles = scrape_styles(data)
    if styles == []:
        print " * Dang, couldn't find anything!\n"
        return
    metadata["genre"] = styles
    print '\n'

register_album_metadata_processor(allmusic_genre)
