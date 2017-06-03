__author__ = 'jgressmann'

PREFIX = u'SC2 '

import sys
import urllib
import urlparse
import traceback
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

import resources.lib.sc2links as sc2links

def debug(str):
    try:
        xbmc.log(PREFIX + str, xbmc.LOGDEBUG)
    except:
        try:
            xbmc.log(PREFIX + 'try as UTF-8: ' + str.decode(str.encode('utf-8')), xbmc.LOGDEBUG)
        except:
            xbmc.log(PREFIX + ' exception, repr: ' + repr(str), xbmc.LOGDEBUG)


def build_url(query):
    return sys.argv[0] + '?' + urllib.urlencode(query)

addon = xbmcaddon.Addon()
addonname = addon.getAddonInfo('name')

handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])
debug("url args: " + str(args))

sc2 = sc2links.Sc2Links()

revealMatches = addon.getSetting('reveal_matches') == 'true'
debug('reveal matches: ' + str(revealMatches))

def get_youtube_info(url):
    # parse something like https://www.youtube.com/watch?v=XqywDF675kQ
    parsed = urlparse.urlparse(url)
    args = urlparse.parse_qs(parsed.query)
    #debug(str(args))
    time = args.get('t', [""])[0]
    id = args.get('v', [""])[0]
    if not id:
        # parse something like https://youtu.be/3A3guAd42Dw?t=9
        if parsed.hostname == 'youtu.be':
            pathParts = (parsed.path or '').split('/')
            if len(pathParts) == 2:
                id = pathParts[1]


    if id:
        return (id, time)


def add_video(v):
    data = get_youtube_info(v.url)
    id = data[0]
    time = data[1]
    if id:
        item = xbmcgui.ListItem()
        videoLabels = {}
        if v.date:
            videoLabels['date'] = v.date.strftime("%d.%m.%Y") #date : string (d.m.Y / 01.01.2009) - file date
            videoLabels['aired'] = v.date.strftime("%Y-%m-%d") #aired : string (2008-12-07)
            videoLabels['year'] = v.date.year #year : integer (2009)
            # dateadded: string(Y - m - d h:m:s = 2009 - 04 - 05 23:16:04)


        item.setInfo('video', videoLabels)

        if revealMatches and v.extra:
            label = u'{} - {}'.format(v.name, v.extra)
            #debug(u'label: ' + label)
            item.setLabel(label)
        else:
            item.setLabel(v.name)

        url = build_url({
            #'youtube': 'plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid={}'.format(id),
            'youtube': 'plugin://plugin.video.youtube/play/?video_id={}'.format(id),
            'time': time})
        # http://kodi.wiki/view/Add-on:YouTube
        # plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid=$VIDEOID

        xbmcplugin.addDirectoryItem(handle, url, item)
    else:
        debug('Could not find video id in {}'.format(v.url))


def build(path):
    slashPath = u'/'.join(path);
    #debug('path2: ' + slashPath)
    if 1 == len(path):
        sc2.load()
        groupings = getattr(sc2, path[0])
        if callable(groupings):
            groupings = groupings()

        for g in groupings:
            url = build_url({'path': u'{}/{}'.format(slashPath, g.name), 'link': g.url})
            xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem(g.name), isFolder=1)

    else:
        link = args.get('link', [""])[0]
        if link:
            debug('link: ' + link)
            collection = sc2links.Collection(path[1], link)
            collection.load()
            if 2 == len(path):
                for child in collection.children:
                    url = build_url({
                        'path': u'{}/{}'.format(slashPath, child.name),
                        'link': link})
                    xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem(child.name), isFolder=1)
            else:
                byHeading = [g for g in collection.children if g.name == path[2]]
                debug(u"with heading: " + str(len(byHeading)))
                if len(byHeading):
                    debug("#video: " + str(len(byHeading[0].videos)))
                    for v in byHeading[0].videos:
                        debug("video: " + v.url)
                        add_video(v)


def play_youtube(url, args):
    time = args.get('time', [''])[0]
    # stop whatever is playing
    player = xbmc.Player()
    player.stop()

    # launch youtube plugin
    xbmc.executebuiltin('PlayMedia({})'.format(url))

    # seek?
    if time:
        delay = 5
        try:
            delay = int(addon.getSetting('youtube_seek_delay_s'))
        except:
            pass

        timeout = 20
        try:
            timeout = int(addon.getSetting('youtube_seek_delay_s'))
        except:
            pass

        # xbmcgui.Dialog().ok(addonname, "have time: " + time)
        # wait for playback
        if timeout > 0:
            for i in range(0, timeout):
                if player.isPlaying():
                    debug('player is playing')
                    break

                xbmc.sleep(1000)

        # seek
        if player.isPlaying() and delay > 0:
            xbmc.sleep(delay * 1000)
            player.seekTime(int(time))


try:
    url = args.get('youtube', [''])[0]
    if url:
        play_youtube(url, args)

    else:
        path = args.get('path', ['/'])[0]
        debug('path1: ' + str(path))
        splitPath = filter(None, path.split('/'))
        debug('path1 len: ' + str(len(splitPath)))
        if len(splitPath) == 0:
            #debug('toplevel')
            url = build_url({'path': '/new'})
            xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem('New'), isFolder=1)
            url = build_url({'path': '/most_recent'})
            xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem('Most Recent'), isFolder=1)
            url = build_url({'path': '/tournaments'})
            xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem('Tournaments'), isFolder=1)
            url = build_url({'path': '/shows'})
            xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem('Shows'), isFolder=1)
        else:
            build(splitPath)

except Exception as e:
    debug(u'Exception: ' + str(e))
    map(debug, str(traceback.format_exc()).splitlines())

xbmcplugin.endOfDirectory(handle)

