# -*- coding: utf-8 -*-
import os
import sys
import urllib2
import shutil
import json
import codecs
import re
import HTMLParser
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3NoHeaderError

import vk_api
import config

from time import time
from progressbar import ProgressBar

def get_token(client_id, **user):
    if not user.get('scope'):
        user['scope'] = (['audio'])
    
    token, uid = vk_api.auth(
        user.get('username'),
        user.get('password'),
        client_id,
        ",".join(user.get('scope'))
    )

    return (token, uid)


def get_audio(token, uid):
    res = vk_api.call_method('audio.getCount', {'oid': uid}, token)
    audio_cnt = res.get('response')

    if audio_cnt and audio_cnt > 0:
        res = vk_api.call_method('audio.get', {'count': audio_cnt}, token)
        return res.get('response')


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


def set_id3(filename, **track):
    try:
        mp3info = EasyID3(filename)
    except ID3NoHeaderError:
        mp3info = EasyID3()

    mp3info['title'] = track.get('title')
    mp3info['artist'] = track.get('artist')
    mp3info.save(filename) 


def save_tracks(filename, tracks):
    if not tracks:
        return

    fields = sorted(tracks[0].keys())

    with codecs.open(filename, 'w', 'utf-8') as fp:
        fp.write('%s\n' % ('\t'.join(fields)))

        for track in tracks:
            fp.write('%s\n' % ('\t'.join([unicode(track.get(f,"")) for f in fields])))


def open_tracks(filename):
    with codecs.open(filename, 'r', 'utf8') as fp:
        firstline = fp.next()
        fields = firstline.rstrip('\n').split('\t')
        for line in fp:
            track = dict(zip(fields, line.rstrip('\n').split('\t')))
            yield track


def download_tracks(tracks, storage_path='files'):
    storage_path = os.path.expanduser(storage_path)
    
    if tracks and not os.path.exists(storage_path):
        os.makedirs(storage_path)
    
    track_cnt = 1
    for track in tracks:
        track['aid'] = str(track.get('aid'))
        track['artist'] = clean_audio_tag(track.get('artist'))
        track['title'] = clean_audio_tag(track.get('title'))

        filename = os.path.basename(track.get('url')).split('?')[0]
        filepath = os.path.join(storage_path, "%s_%s" % (track.get('aid'), filename))

        if os.path.isfile(filepath):
            print 'Skipped "%(artist)s - %(title)s"' % (track)
            continue

        print '[%d/%d] ' % (track_cnt, len(tracks)) + 'Downloading "%(artist)s - %(title)s"...' % (track)
        
        try:
            req = urllib2.urlopen(track.get('url'))
            total = req.headers.get('content-length') or 0
            #print "total: %s" % (total)
            
            bar = None
            if total:
                bar = ProgressBar(maxval=int(total)).start()

            with open(filepath, 'wb') as fp:
                chunk_size = 16 * 1024
                loaded = 0
                
                for chunk in iter(lambda: req.read(chunk_size), ''):
                    fp.write(chunk)

                    if total:
                        loaded += len(chunk)
                        bar.update(loaded)
            
            if total:
                bar.finish()

            set_id3(filepath, **track)
            track_cnt+=1

        except urllib2.HTTPError, err:
            print "HTTPError:", err
            
        except IOError, err:
            print "IOError:", err
    
  
def main():
    
    playlist = 'playlist.txt'
    tracks = []

    if not os.path.isfile(playlist):

        user = {
            'username': config.USERNAME,
            'password': config.PASSWORD,
            'scope': (['audio']),
        }

        client_id = config.CLIENT_ID

        tracks = get_audio(*get_token(client_id, **user))
        save_tracks(playlist, tracks)

    else:
        tracks = list(open_tracks(playlist))


    download_tracks(tracks, config.MUSIC_PATH)
    
    
    print 'done.'


if __name__ == '__main__':
    main()

