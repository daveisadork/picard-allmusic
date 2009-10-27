# -*- coding: utf-8 -*-

PLUGIN_NAME = u"AllMusic Genres"
PLUGIN_AUTHOR = u"Dave Hayes"
PLUGIN_DESCRIPTION = "Scrape AllMusic for Genre Tags"
PLUGIN_VERSION = "0.1"
PLUGIN_API_VERSIONS = ["0.9.0", "0.10"]

from PyQt4 import QtCore
from picard.ui.options import register_options_page, OptionsPage
from picard.config import BoolOption, IntOption, TextOption
#from picard.plugins.allmusic.ui_options_allmusic import Ui_AllMusicOptionsPage
from picard.metadata import register_album_metadata_processor, register_track_metadata_processor
from picard.util import partial
from difflib import get_close_matches
from BeautifulSoup import BeautifulSoup
import re

def finalize_genres(styles, metadata, target, albumtitle, albumartist, album):
    if styles == [] and target == "album_data":
        album._requests += 1
        album.tagger.xmlws.add_task(partial(artist_search, album, metadata, albumtitle), position=1)
    elif styles == []:
        print " * Dang, couldn't find anything!",
    else:
        metadata["genre"] = styles
        for track in album._new_tracks:
            track.metadata["genre"] = styles
        print ""

def scrape_styles(html, album, target, albumtitle, albumartist, metadata):
    styles = []
    try:
        print " * Scraping styles:",
        for style in html.find(text="Genre Listing").findNext('ul').findAll('a'):
            styles.append(style.contents[0].replace("/ ","/"))
        if styles == []:
            print "none"
        for style in styles:
            if style != styles[0]:
                print "\b, " + style,
            else:
                print style,
    except:
        pass
    finally:
        print "\n",
        finalize_genres(styles, metadata, target, albumtitle, albumartist, album)
        metadata["genre"] = styles
        album._requests -= 1

def parse_album_search(search_results, albumartist, albumtitle):
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
        return None
    print "[ OK ]"
    for records in results:
        strings.append(records[2])
    search_string = albumartist + albumtitle
    print " * Looking for a close match:",
    match = get_close_matches(search_string, strings, 1, 0.6)
    if match == []:
        print "none"
        return None
    for search in results:
        if match[0] == search[2].encode('utf-8'):
            print search[1] + " by " + search[0]
            return search[3]

def sanitize_data(data, albumartist):
    data = data.replace('style=padding-right:20px;"','')
    if albumartist == u"Various Artists":
        data = data.replace('<class="subtitle">Various Artists', '<a href="" class="subtitle">Various Artists</a>')
    data = re.sub(r"(?is)(<script[^>]*>)(.*?)(</script>)", "\1\3", data)
    return data

def _data_downloaded(album, target, albumtitle, albumartist, metadata, data, http, error):
    try:
        if error:
            print "[fail]"
            album.log.error(str(http.errorString()))
        else:
            print "[ OK ]"
            data = sanitize_data(data, albumartist)
            try:
                html = BeautifulSoup(data)
            except:
                print "\nCRAP! Looks like we're getting bad HTML from allmusic.com\n"
                if target == "album_search" or target == "album_data":
                    album._requests += 1
                    print " * Sending artist search request",
                    artist_search(album, metadata, albumtitle)
                    return
                if target == "artist_search" or target == "artist_data":
                    return
            if target == "album_search":
                album._requests += 1
                album_url = parse_album_search(html, albumartist, albumtitle)
                if not album_url and albumartist != "Various Artists":
                    print " * Sending artist search request",
                    artist_search(album, metadata, albumtitle)
                else:
                    print " * Requesting album data",
                    get_data(album_url, "album_data", albumtitle, albumartist, album, metadata)
            if target == "album_data" or target == "artist_data" or target == "artist_search":
                album._requests += 1
                scrape_styles(html, album, target, albumtitle, albumartist, metadata)
    finally:
        album._requests -= 1
        album._finalize_loading(None)

def get_data(path, target, albumtitle, albumartist, album, metadata):
    try:
        album._requests += 1
        album.tagger.xmlws.download("allmusic.com", 80, str(path),
        partial(_data_downloaded, album, target, albumtitle, albumartist, metadata), position=1)
    finally:
        album._requests -= 1
    return False

def album_search(album, metadata, albumtitle):
    path = "/cg/amg.dll?p=amg&opt1=2&sql=" + QtCore.QUrl.toPercentEncoding(unicode(albumtitle))
    return get_data(path, "album_search", albumtitle, metadata["albumartist"], album, metadata)

def artist_search(album, metadata, albumtitle):
    path = "/cg/amg.dll?p=amg&opt1=1&sql=" + QtCore.QUrl.toPercentEncoding(unicode(metadata["albumartist"]))
    return get_data(path, "artist_search", albumtitle, metadata["albumartist"], album, metadata)

def clean_album_title(albumtitle):
    albumtitle = re.sub(r"\s+\(disc (\d+)(?::\s+([^)]+))?\)", r"", albumtitle)
    albumtitle = re.sub(r"\s+\(bonus disc(?::\s+([^)]+))?\)", r"", albumtitle)
    return albumtitle

def allmusic_genre(album, metadata, release):
    albumtitle = clean_album_title(metadata["album"])
    print " * Looking for " + albumtitle + " by " + metadata["albumartist"]
    print " * Sending album search request",
    album._requests += 1
    album.tagger.xmlws.add_task(partial(album_search, album, metadata, albumtitle), position=1)

register_album_metadata_processor(allmusic_genre)
#register_options_page(AllMusicOptionsPage)
