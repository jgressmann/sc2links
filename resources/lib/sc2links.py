__author__ = 'jgressmann'

from bs4 import BeautifulSoup
import datetime
from dateutil.parser import parse as parse_datetime

import requests
import urlparse


def get_bs(url):
    r = requests.get(url)
    if not r.ok:
        raise IOError('Failed to get {}, code {}'.format(url, r.status_code))

    return BeautifulSoup(r.content, 'html.parser')

def replace_html_entities(str):
    #print('replace html in: ' + repr(str))
    str = str or ''
    str = str.replace(u'\xa0', ' ')
    #print('replace html out: ' + repr(str))
    return str

def cleanup_html_strings(strings):
    #print('cleanup html in: ' + repr(strings))
    strings = map(replace_html_entities, strings)
    strings = map(lambda x: x.strip(), strings)
    strings = filter(lambda x: x, strings)
    #print('cleanup html in: ' + repr(strings))
    return strings


def keep_text(s):
    if s.lower().startswith('reveal'):
        return False
    if s.lower() == 'vs':
        return False
    return True


def is_date(str):
    try:
        date = parse_datetime(str)
        return True
    except Exception as e:
        return False

def level2(context):
    return context['vods']

def level1(context):
    result = []
    url = context['url']
    year = context['year']
    tournamentSoup = get_bs(url)

    #tournamentPageStageNameRegex(QStringLiteral("<h3>([^>]+)</h3>\\s*<h5>"));
    for h3 in tournamentSoup.find_all('h3'):
        sibling = h3.next_sibling
        if not sibling:
            break # done

        if sibling.name != 'h5':
            continue # not a potential match list

        if sibling.previous_sibling != h3:
            continue # too far

        texts = cleanup_html_strings(h3.stripped_strings)
        stageName = u' '.join(texts)
        vods = []
        tag = sibling

        while True:
            if not tag:
                break

            if tag.name == 'h3':
                break

            if tag.name == 'h5':
                if len(tag.contents) == 4:
                    vodPageUrl = tag.contents[0].get('href')
                    matchString = cleanup_html_strings(tag.contents[0].stripped_strings)[0]
                    matchNumber = int(matchString.split(' ')[1])
                    dateString = cleanup_html_strings(tag.contents[3].stripped_strings)[0]
                    month = dateString[0:2]
                    day = dateString[3:5]
                    date = datetime.date(year, int(month), int(day))

                    texts = cleanup_html_strings(tag.contents[2].stripped_strings)
                    texts = filter(keep_text, texts)
                    side1 = texts[0] if len(texts) > 0 else ''
                    side2 = texts[1] if len(texts) > 0 else ''

                    vods.append(Vod(match_number=matchNumber, date=date, url=vodPageUrl, side1=side1, side2=side2))


            tag = tag.next_sibling

        for vod in vods:
            vod.match_count = len(vods)


        result.append(Item(name=stageName, year=year, ctx={'vods': vods}, fetch_children=level2))


    return result

def level0(*arg):
    result = []
    soup = get_bs('https://www.sc2links.com/vods/')
    #<a href="https://www.sc2links.com/tournament/?match=502">WCS Montreal</a></div><div class="voddate">September 11th 2017</div></br>
    for link in soup.find_all('a'):
        href = link.get('href')
        #print(Sc2Links.DOMAIN + '/tournament/?match=')
        print(href)
        if href and href.startswith('https://www.sc2links.com/tournament/?match='):
            texts = cleanup_html_strings(link.stripped_strings)
            name = u' '.join(texts)
            year = 0
            dateString = u' '.join(link.find_next('div').strings)
            for s in dateString.split(' '):
                if len(s) == 4 and s.isdigit():
                    year = int(s)
                    break

            result.append(Item(name=name, year=year, ctx={ 'url': href, 'year': year }, fetch_children=level1))

    return result

def level0_done(*arg):
    ctx = { 'url': 'https://www.sc2links.com/tournament/?match=509', 'year': 2017 }
    return [Item(name='WCS Grand Finals', year=2017, ctx=ctx, fetch_children=level1)]

class Vod:
    def __init__(self, **kwargs):
        self.match_number = 0
        self.match_count = 0
        self.year = 0
        self.date = None
        self._url = None
        self.side1 = None
        self.side2 = None
        self._vod_url = None
        for key in kwargs:
            if key == 'date':
                self.date = kwargs[key]
            elif key == 'url':
                self._url = kwargs[key]
            elif key == 'match_number':
                self.match_number = kwargs[key]
            elif key == 'match_count':
                self.match_count = kwargs[key]
            elif key == 'side1':
                self.side1 = kwargs[key]
            elif key == 'side2':
                self.side2 = kwargs[key]

    def __repr__(self):
        return "{side1=" + repr(self.side1) + ", side2=" + repr(self.side2) + ", date=" + repr(self.date) + ", match_number=" + repr(self.match_number) + ", match_count=" + repr(self.match_count) + ", _url=" + repr(self._url) + ", _vod_url=" + ("?" if self._vod_url is None else self._vod_url) + "}"

    @property
    def url(self):
        if not self._vod_url:
            if self._url:
                matchSoup = get_bs(self._url)
                iframe = matchSoup.find('iframe')
                if iframe:
                    self._vod_url = iframe.get('src')

        return self._vod_url


class Item:
    def __init__(self, **kwargs):
        self._children = None
        self.name = None
        self.year = 0
        self.fetch_children = None
        self.ctx = None
        for key in kwargs:
            if key == 'name':
                self.name = kwargs[key]
            elif key == 'year':
                self.year = kwargs[key]
            elif key == 'fetch_children':
                self.fetch_children = kwargs[key]
            elif key == 'ctx':
                self.ctx = kwargs[key]


    @property
    def children(self):
        if None is self._children:
            self._children = self._fetch()
        return self._children


    def _fetch(self):
        if None is self.fetch_children:
            return []
        return self.fetch_children(self.ctx)

    def __repr__(self):
        return "{ name=" + repr(self.name) + ", year=" + repr(self.year) + ", children=" + ("?" if self._children is None else repr(len(self._children))) + " }"

class Sc2Links(Item):
    LEVELS = 3
    def __init__(self):
        Item.__init__(self, fetch_children=level0)

