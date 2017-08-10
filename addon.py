__author__ = 'jgressmann'

import sys
import traceback
import urllib
import urlparse
#import urlresolver
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

import resources.lib.sc2links as sc2links

addon = xbmcaddon.Addon()
#__addonname__ = addon.getAddonInfo('name')
addonid = addon.getAddonInfo('id')

def debug(val):
    if isinstance(val, str) or isinstance(val, unicode):
        pass
    else:
        val = repr(val)

    message = u'%s: %s' % (addonid, val)

    xbmc.log(message.encode('utf-8'), xbmc.LOGDEBUG)


def build_url(query):
    return sys.argv[0] + '?' + urllib.urlencode(query)



handle = int(sys.argv[1])
args = dict(urlparse.parse_qsl(sys.argv[2][1:]))
debug("url args: " + repr(args))

sc2 = sc2links.Sc2Links()

revealMatches = addon.getSetting('reveal_matches') == 'true'
debug('reveal matches: ' + str(revealMatches))

def get_youtube_info(url):
    # parse something like https://www.youtube.com/watch?v=XqywDF675kQ
    parsed = urlparse.urlparse(url)
    args = urlparse.parse_qs(parsed.query)
    #debug(str(args))
    time = args.get('t', [''])[0]
    id = args.get('v', [''])[0]
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

        item.setProperty('StartOffset', time or '0')

        # # try to use urlresolver
        mediaUrl = None
        # try:
        #     mediaUrl = urlresolver.resolve(v.url)
        # except:
        #     pass

        if mediaUrl:
            debug(u'resolve youtube url:' + mediaUrl)
            xbmcplugin.addDirectoryItem(handle, mediaUrl, item, False)
        else:
            # fallback to manually calling the youtube plugin
            url = build_url({
                # 'youtube': 'plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid={}'.format(id),
                'youtube': 'plugin://plugin.video.youtube/play/?video_id={}'.format(id),
                'time': time})

            xbmcplugin.addDirectoryItem(handle, url, item, False)

            #item.setPath(v.url)
            #xbmcplugin.addDirectoryItem(handle, 'plugin://plugin.video.youtube/play/?video_id={}'.format(id), item, False)
    else:
        debug('Could not find video id in {}'.format(v.url))

def get_year_from_args(args):
    year = args.get('year', [None])[0]
    if year:
        year = int(year)
    return year

def build_show():
    # year = get_year_from_args(args)
    # debug('year: ' + str(year))
    # name = get_name_from_args(args)
    # debug('name: ' + name)
    link = args.get('link', None)
    debug('link: ' + link)
    match = args.get('match', None)
    debug('match: ' + str(match))

    collection = sc2links.Collection('dummy', link)
    collection.load()
    if match is None:
        for child in collection.children:
            args.update({'match': child.name})
            url = build_url(args)
            xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem(child.name), isFolder=1)
    else:
        byHeading = [g for g in collection.children if g.name == match]
        debug(u"with heading: " + str(len(byHeading)))
        if len(byHeading):
            debug("#video: " + str(len(byHeading[0].videos)))
            for v in byHeading[0].videos:
                debug("video: " + v.url)
                add_video(v)

def by_name(lhs, rhs):
    return cmp(lhs.name, rhs.name)

def build_by_name():
    topic = args.get('topic', None)
    name = args.get('name', None)
    year = args.get('year', None)
    if None is name:
        sc2.load()
        groupings = getattr(sc2, topic)
        if callable(groupings):
            groupings = groupings()

        # def by_year_then_by_name(lhs, rhs):
        #     lhsY = lhs.year
        #     rhsY = rhs.year
        #     if lhsY:
        #         if rhsY:
        #             # debug('lhs y={} n={}, rhs y={} n={}'.format(lhs.year, lhs.name, rhs.year, rhs.name))
        #             res = cmp(lhsY, rhsY)
        #             if 0 != res:
        #                 return -res
        #             return by_name(lhs, rhs)
        #         return -1
        #     else:
        #         if rhsY:
        #             return 1
        #         return by_name(lhs, rhs)

        sortedByName = sorted(groupings, cmp=by_name)
        for g in sortedByName:
            args.update({'name': g.name, 'link': g.url})
            url = build_url(args)
            xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem(g.name), isFolder=1)
    elif None is year:
        debug('name: ' + name)
        sc2.load()
        groupings = getattr(sc2, topic)
        if callable(groupings):
            groupings = groupings()

        filtered = [item for item in groupings if item.name == name]
        years = [x.year for x in filtered]
        years = set(years)
        years = sorted(years, reverse=True)
        debug('years: ' + repr(years))
        for year in years:
            displayYear = str(year or 'Other')
            args.update({'year': year or -1})
            url = build_url(args)
            xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem(displayYear), isFolder=1)
    else:
        build_show()


def build_by_year():
    topic = args.get('topic', None)
    year = args.get('year', None)
    name = args.get('name', None)

    if None is year:
        sc2.load()
        groupings = getattr(sc2, topic)
        if callable(groupings):
            groupings = groupings()

        years = [x.year for x in groupings]
        years = set(years)
        years = sorted(years, reverse=True)
        debug('years: ' + repr(years))
        for year in years:
            displayYear = str(year or 'Other')
            args.update({'year': year or -1})
            url = build_url(args)
            xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem(displayYear), isFolder=1)
    elif None is name:


        year = int(year)
        if -1 == year:
            year = None

        debug('year: ' + str(year))
        sc2.load()
        groupings = getattr(sc2, topic)
        if callable(groupings):
            groupings = groupings()

        filtered = [item for item in groupings if item.year == year]
        sortedByName = sorted(filtered, cmp=by_name)
        for g in sortedByName:
            args.update({'name': g.name, 'link': g.url})
            url = build_url(args)
            xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem(g.name), isFolder=1)
    else:
        build_show()


def build_topic():
    order = args.get('order', None)
    if None is order:
        args.update({'order': 0})
        url = build_url(args)
        xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem('By Name'), isFolder=1)

        args.update({'order': 1})
        url = build_url(args)
        xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem('By Year'), isFolder=1)

    else:
        order = int(order)
        if order == 1:
            build_by_year()
        else:
            build_by_name()

    # if 1 == len(path):
    #     sc2.load()
    #     groupings = getattr(sc2, path[0])
    #     if callable(groupings):
    #         groupings = groupings()
    #
    #     def by_year_then_by_name(lhs, rhs):
    #         lhsY = lhs.year
    #         rhsY = rhs.year
    #         if lhsY:
    #             if rhsY:
    #                 #debug('lhs y={} n={}, rhs y={} n={}'.format(lhs.year, lhs.name, rhs.year, rhs.name))
    #                 res = cmp(lhsY, rhsY)
    #                 if 0 != res:
    #                     return -res
    #                 return by_name(lhs, rhs)
    #             return -1
    #         else:
    #             if rhsY:
    #                 return 1
    #             return by_name(lhs, rhs)
    #
    #     years = [x.year for x in groupings]
    #     years = set(years)
    #     years = sorted(years, reverse=True)
    #     debug('years: ' + repr(years))
    #     for year in years:
    #         displayYear = str(year or 'Other')
    #         url = build_url({'path': u'{}/{}'.format(slashPath, displayYear), 'year': year})
    #         xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem(displayYear), isFolder=1)
    #
    # elif 2 == len(path):
    #     year = get_year_from_args(args)
    #     debug('year: ' + str(year))
    #     sc2.load()
    #     groupings = getattr(sc2, path[0])
    #     if callable(groupings):
    #         groupings = groupings()
    #
    #     filtered = [item for item in groupings if item.year == year]
    #     sortedByName = sorted(filtered, cmp=by_name)
    #     for g in sortedByName:
    #         url = build_url({'path': u'{}/{}'.format(slashPath, g.name), 'year': year, 'link': g.url})
    #         xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem(g.name), isFolder=1)
    # else:
    #     year = get_year_from_args(args)
    #     debug('year: ' + str(year))
    #     link = args.get('link', [""])[0]
    #     if link:
    #         debug('link: ' + link)
    #         collection = sc2links.Collection(path[1], link)
    #         collection.load()
    #         if 3 == len(path):
    #             for child in collection.children:
    #                 url = build_url({
    #                     'path': u'{}/{}'.format(slashPath, child.name),
    #                     'year': year,
    #                     'link': link})
    #                 xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem(child.name), isFolder=1)
    #         else:
    #             byHeading = [g for g in collection.children if g.name == path[3]]
    #             debug(u"with heading: " + str(len(byHeading)))
    #             if len(byHeading):
    #                 debug("#video: " + str(len(byHeading[0].videos)))
    #                 for v in byHeading[0].videos:
    #                     debug("video: " + v.url)
    #                     add_video(v)


def play_youtube(url, args):
    time = args.get('time', '')
    # BROKEN URL RESOLVER
    # media_url = urlresolver.resolve('https://www.youtube.com/watch?v=7OXVPgu6urw')
    # # Create a playable item with a path to play.
    # play_item = xbmcgui.ListItem(path=url)
    # play_item.setProperty('StartOffset', time)
    # # Pass the item to the Kodi player.
    # xbmcplugin.setResolvedUrl(handle, True, listitem=play_item)
    # return


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
    url = args.get('youtube', '')
    if url:
        play_youtube(url, args)

    else:
        topic = args.get('topic', None)
        if not topic:
            args.update({'topic': 'new'})
            url = build_url(args)
            xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem('New'), isFolder=1)
            args.update({'topic': 'most_recent'})
            url = build_url(args)
            xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem('Most Recent'), isFolder=1)
            args.update({'topic': 'tournaments'})
            url = build_url(args)
            xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem('Tournaments'), isFolder=1)
            args.update({'topic': 'shows'})
            url = build_url(args)
            xbmcplugin.addDirectoryItem(handle, url, xbmcgui.ListItem('Shows'), isFolder=1)
        else:
            debug('topic: ' + str(topic))
            build_topic()

except Exception as e:
    debug(u'Exception: ' + str(e))
    map(debug, str(traceback.format_exc()).splitlines())

xbmcplugin.endOfDirectory(handle)

