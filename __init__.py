# -*- coding: utf-8 -*-

PLUGIN_NAME = u"AllMusic Genres"
PLUGIN_AUTHOR = u"Dave Hayes"
PLUGIN_DESCRIPTION = "Scrape AllMusic for Genre Tags"
PLUGIN_VERSION = "0.1"
PLUGIN_API_VERSIONS = ["0.9.0", "0.10"]

try:
    from BeautifulSoup import BeautifulSoup
except:
    try:
        from picard.plugins.allmusic.BeautifulSoup import BeautifulSoup
    except:
        raise ImportError, "Could not import BeautifulSoup. Get it at http://www.crummy.com/software/BeautifulSoup/"
from PyQt4 import QtCore
from picard.ui.options import register_options_page, OptionsPage
from picard.config import BoolOption, IntOption, TextOption
#from picard.plugins.allmusic.ui_options_allmusic import Ui_AllMusicOptionsPage
from picard.metadata import register_album_metadata_processor, register_track_metadata_processor
from picard.util import partial, translate_artist
from picard.similarity import similarity2
import re

def ununicode (unicrap):
    xlate={0xc0:'A', 0xc1:'A', 0xc2:'A', 0xc3:'A', 0xc4:'A', 0xc5:'A',
        0xc6:'Ae', 0xc7:'C',
        0xc8:'E', 0xc9:'E', 0xca:'E', 0xcb:'E',
        0xcc:'I', 0xcd:'I', 0xce:'I', 0xcf:'I',
        0xd0:'Th', 0xd1:'N',
        0xd2:'O', 0xd3:'O', 0xd4:'O', 0xd5:'O', 0xd6:'O', 0xd8:'O',
        0xd9:'U', 0xda:'U', 0xdb:'U', 0xdc:'U',
        0xdd:'Y', 0xde:'th', 0xdf:'ss',
        0xe0:'a', 0xe1:'a', 0xe2:'a', 0xe3:'a', 0xe4:'a', 0xe5:'a',
        0xe6:'ae', 0xe7:'c',
        0xe8:'e', 0xe9:'e', 0xea:'e', 0xeb:'e',
        0xec:'i', 0xed:'i', 0xee:'i', 0xef:'i',
        0xf0:'th', 0xf1:'n',
        0xf2:'o', 0xf3:'o', 0xf4:'o', 0xf5:'o', 0xf6:'o', 0xf8:'o',
        0xf9:'u', 0xfa:'u', 0xfb:'u', 0xfc:'u',
        0xfd:'y', 0xfe:'th', 0xff:'y',
        0xa1:'!', 0xa2:'{cent}', 0xa3:'{pound}', 0xa4:'{currency}',
        0xa5:'{yen}', 0xa6:'|', 0xa7:'{section}', 0xa8:'{umlaut}',
        0xa9:'{C}', 0xaa:'{^a}', 0xab:'<<', 0xac:'{not}',
        0xad:'-', 0xae:'{R}', 0xaf:'_', 0xb0:'{degrees}',
        0xb1:'{+/-}', 0xb2:'{^2}', 0xb3:'{^3}', 0xb4:"'",
        0xb5:'{micro}', 0xb6:'{paragraph}', 0xb7:'*', 0xb8:'{cedilla}',
        0xb9:'{^1}', 0xba:'{^o}', 0xbb:'>>', 
        0xbc:'{1/4}', 0xbd:'{1/2}', 0xbe:'{3/4}', 0xbf:'?',
        0xd7:'*', 0xf7:'/'
        }

    r = ''
    for i in unicrap:
        if xlate.has_key(ord(i)):
            r += xlate[ord(i)]
        elif ord(i) >= 0x80:
            pass
        else:
            r += str(i)
    return r

def get_close_matches(search_string, search_set, max_results, min_score):
    winners = []
    matches = []
    for items in search_set:
        score = similarity2(search_string, items)
        if score > min_score:
            winners.append([score, items])
    if winners == []:
        return []
    winners.sort()
    winners.reverse()
    for items in winners:
        if len(matches) < max_results:
            matches.append(items[1])
            print items[0],
    return matches

def finalize_genres(styles, metadata, target, albumtitle, albumartist, album):
    if styles == [] and target == "album_data" and albumartist != "Various Artists":
        album._requests += 1
        album.tagger.xmlws.add_task(partial(artist_search, album, metadata, albumtitle, albumartist), position=1)
    elif styles == []:
        print " * Dang, couldn't find anything!\n"
    else:
        metadata["genre"] = styles
        for track in album._new_tracks:
            track.metadata["genre"] = styles
        print "\n"

def scrape_styles(html, album, target, albumtitle, albumartist, metadata):
    styles = []
    try:
        print " * Scraping styles:",
        for style in html.find(text="Genre Listing").findNext('td').div.ul.findAll('a'):
            styles.append(style.contents[0].replace("/ ","/"))
        if styles == []:
            print "none"
        for style in styles:
            if style != styles[0]:
                print "\b, " + style,
            else:
                print style,
    except:
        print "none"
    finally:
        finalize_genres(styles, metadata, target, albumtitle, albumartist, album)
        metadata["genre"] = styles
        album._requests -= 1

def parse_artist_search(search_results, albumartist):
    brackets = re.compile(r" \[.*]")
    results = []
    artists = []
    print " * Parsing artist search results",
    try:
        for listings in search_results.find(id="results-table").findAll('tr'):
            try:
                artist_string = listings.find(style="width:290px;word-wrap:break-word;").find('a').string
                artist_url = listings.find(style="width:290px;word-wrap:break-word;").find('a')['href']
                artist_string = re.sub(r" \[.*]", r"", artist_string)
                results.append([artist_string,artist_url])
                artists.append(artist_string)
            except:
                pass
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
        return None
    print match[0]
    for search in results:
        if match[0] == search[0]:
           return search[1]
    return None

def parse_album_search(search_results, albumartist, albumtitle):
    results = []
    strings = []
    artists = []
    condense = []
    titles = []
    print " * Parsing album search results",
    try:
        for listings in search_results.find(id="results-table").findAll('tr', attrs={"class" : "visible"}):
            try:
                artist_string = listings.find(style="width:206px;word-wrap:break-word;").string
                album_string = listings.find(style="width:230px;word-wrap:break-word;").a.string
                album_url = listings.find(style="width:230px;word-wrap:break-word;").a["href"]
                artist_string = artist_string.replace('Original Soundtrack','Various Artists')
                search_string = artist_string + album_string
                results.append([artist_string, album_string, search_string, album_url])
            except:
                pass
    except:
        pass
    if results == []:
        print "[fail]"
        return None
    print "[ OK ]"
    for records in results:
        strings.append(records[2])
        artists.append(records[0])
    print " * Looking for a close match:",
    artist_match = get_close_matches(albumartist, artists, 3, 0.85)
    if artist_match != []:
        for search in results:
            for items in artist_match:
                if items == search[0]:
                    if search[3] in condense:
                        pass
                    else:
                        condense.append(search)
        for records in condense:
            titles.append(records[1])
        album_match = get_close_matches(albumtitle, titles, 1, 0.75)
        if album_match != []:
            for search in condense:
                if album_match[0] == search[1]:
                    print search[1] + " by " + search[0]
                    return search[3]
    search_string = albumartist + albumtitle
    match = get_close_matches(search_string, strings, 1, 0.75)
    if match == []:
        print "none"
        return None
    for search in results:
        if match[0] == search[2]:
            print search[1] + " by " + search[0]
            return search[3]
    return None

def sanitize_data(data, albumartist):
    data = data.replace('style=padding-right:20px;"','')
    if albumartist == u"Various Artists":
        data = data.replace('<class="subtitle">Various Artists', '<a href="" class="subtitle">Various Artists</a>')
    data = re.sub(r"(?is)(<script[^>]*>)(.*?)(</script>)", " ", data)
    data = data.replace('&amp;', '&')
    return data

def _data_downloaded(album, target, albumtitle, albumartist, metadata, data, http, error):
    try:
        if error:
            print "[fail] "
            print str(http.errorString())
            album.log.error(str(http.errorString()))
        else:
            print "[ OK ] "
            data = sanitize_data(data, albumartist)
            try:
                html = BeautifulSoup(data)
            except:
                print " * CRAP! Looks like we're getting bad (album) HTML from allmusic.com\n"
                if target == "album_search" or target == "album_data":
                    album._requests += 1
                    print " * Sending artist search request",
                    artist_search(album, metadata, albumtitle, albumartist)
                    return
                if target == "artist_search" or target == "artist_data":
                    return
            if target == "album_search":
                album._requests += 1
                album_url = parse_album_search(html, albumartist, albumtitle)
                if album_url != None:
                    print " * Requesting album data",
                    get_data(album_url, "album_data", albumtitle, albumartist, album, metadata)
                elif albumartist != "Various Artists":
                    print " * Sending artist search request",
                    artist_search(album, metadata, albumtitle, albumartist)
                else:
                    finalize_genres([], metadata, "album_data", albumtitle, albumartist, album)
            try:
                if target == "artist_search" and html.find('title').string == "allmusic":
                    artist_url = parse_artist_search(html, albumartist)
                    if artist_url == None:
                        finalize_genres([], metadata, target, albumtitle, albumartist, album)
                    else:
                        print " * Requesting artist data",
                        album._requests += 1
                        get_data(artist_url, "artist_data", albumtitle, albumartist, album, metadata)
                if target == "album_data" or target == "artist_data" or (target == "artist_search" and html.find('title').string != "allmusic"):
                    album._requests += 1
                    scrape_styles(html, album, target, albumtitle, albumartist, metadata)
            except:
                print " * CRAP! Looks like we're getting bad (artist) HTML from allmusic.com\n"
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

def _post(album, host, port, path, data, handler):
    header = album.tagger.xmlws._prepare("POST", host, port, path)
    album.tagger.xmlws.log.debug("POST-DATA %r", data)
    requestid = album.tagger.xmlws.request(header, data)
    album.tagger.xmlws._request_handlers[requestid] = (handler, False)
    return True

def post(album, host, port, path, data, handler, position=None):
    func = partial(_post, album, host, port, path, data, handler)
    album.tagger.xmlws.add_task(func, position)

def post_data(search_data, target, albumtitle, albumartist, album, metadata):
    print search_data,
    try:
        album._requests += 1
        post(album, "allmusic.com", 80, "/cg/amg.dll", search_data,
        partial(_data_downloaded, album, target, albumtitle, albumartist, metadata), position=1)
    finally:
        album._requests -= 1
    return False

def album_search(album, metadata, albumtitle, albumartist):
    search_data = "P=amg&opt1=2&sql=" + QtCore.QUrl.toPercentEncoding(albumtitle)
    return post_data(search_data, "album_search", albumtitle, albumartist, album, metadata)

def artist_search(album, metadata, albumtitle, albumartist):
    search_data = "P=amg&opt1=1&sql=" + QtCore.QUrl.toPercentEncoding(albumartist)
    return post_data(search_data, "artist_search", albumtitle, albumartist, album, metadata)

def clean_album_title(albumtitle):
    albumtitle = re.sub(r"\s+\(disc (\d+)(?::\s+([^)]+))?\)", r"", albumtitle)
    albumtitle = re.sub(r"\s+\(bonus disc(?::\s+([^)]+))?\)", r"", albumtitle)
    return albumtitle

def allmusic_genre(album, metadata, release):
    if metadata["albumartist"] != "Various Artists":
        albumartist = translate_artist(metadata['artist'], metadata['artistsort'])
    else:
        albumartist = metadata["albumartist"]
    albumtitle = clean_album_title(metadata["album"])
    albumartist = unicode(ununicode(albumartist))
    albumtitle = unicode(ununicode(albumtitle))
    print " * Looking for " + albumtitle + " by " + albumartist
    print " * Sending album search request",
    album._requests += 1
    album.tagger.xmlws.add_task(partial(album_search, album, metadata, albumtitle, albumartist), position=1)

register_album_metadata_processor(allmusic_genre)
#register_options_page(AllMusicOptionsPage)
