# -*- coding: utf-8 -*-
import os
import urllib2
import json
import codecs
import re
import HTMLParser
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError
import urlgrabber

import vk_api
import config

from time import time


def get_token(credentials=[]):
    if not len(credentials):
        credentials = ('friends',)

    token, user_id = vk_api.auth(config.USERNAME,
                                 config.PASSWORD,
                                 config.CLIENT_ID,
                                 ",".join(credentials))    
    return (token, user_id)


def get_audio(token, uid):
    res = vk_api.call_method('audio.getCount', {
        'oid': uid}, token)
    audio_cnt = res['response']

    res = vk_api.call_method('audio.get', {
        'count': audio_cnt}, token)

    return res
    

def clean_audio_tag(tag):
    h = HTMLParser.HTMLParser()
    tag = h.unescape(tag)
    tag = h.unescape(tag) # need to unescape unescaped entities

    tag = re.sub(r'http://.[^\s]+', '', tag) # remove any urls
    tag = tag.replace(' :)','') # remove smiles
    
    ctag = re.compile(u'[^a-zA-Zа-яА-ЯёЁ0-9\s_\.,&#!?\-\'"`\/\|\[\]\(\)]') 
    tag = ctag.sub('', tag).strip() # kill most unusual symbols
    tag = re.sub(r'\s+', ' ', tag) # remove long spaces

    return tag


def set_id3(filename, title, artist):
    try:
        mp3info = EasyID3(filename)
    except ID3NoHeaderError:
        mp3info = EasyID3()

    mp3info['title'] = title
    mp3info['artist'] = artist
    mp3info.save(filename) 


# audio.get
def download_playlist():
    token, user_id = get_token(['audio'])
    user_audio = get_audio(token, user_id)['response']

    with codecs.open(config.PLAYLIST, 'w', 'utf8') as fp:
        for track in user_audio:
            aid = str(track.get('aid'))
            artist = clean_audio_tag(track.get('artist'))
            title = clean_audio_tag(track.get('title'))
            url = track.get('url')
            
            fp.write('%s\n' % ('\t'.join((aid, artist, title, url))))


# download mp3 files
def download_audio_files():

    if not os.path.exists(config.MUSIC_PATH):
        os.makedirs(config.MUSIC_PATH)
    
    for line in open(config.PLAYLIST):
        aid, artist, title, url = line.rstrip('\n').decode('utf-8').split('\t')
        filename = os.path.basename(url).split('?')[0]
        filepath = os.path.join(config.MUSIC_PATH, "%s_%s" % (aid, filename))

        print "Download %s - %s..." % (artist, title)

        g = urlgrabber.grabber.URLGrabber(reget='simple')
        try:
            g.urlgrab(url, filename=filepath)
        except urlgrabber.grabber.URLGrabError, e:
            if e.exception[1] != 'The requested URL returned error: 416 Requested Range Not Satisfiable':
                raise

        set_id3(filepath, title, artist)


def main():

    print 'start...'
    if not os.path.isfile(config.PLAYLIST):
        print 'download playlist...',
        download_playlist()
        print 'ok'
        
    download_audio_files()
    
    print 'done.'


if __name__ == '__main__':
    main()

