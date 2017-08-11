__author__ = 'jgressmann'

from bs4 import BeautifulSoup
import requests
import urlparse
from dateutil.parser import parse as parse_datetime


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

class Video:
    def __init__(self, url, name, date, extra):
        self.url = url
        self.name = name
        self.date = date
        self.extra = extra


class Grouping:
    def __init__(self, name, videos=None):
        self.name = name
        self.videos = videos or []


class Collection:
    def __init__(self, name, url):
        index = name.find(' ')
        if index > 0 and name[:index].isdigit():
            self.year = int(name[:index])
            self.name = name[index:].lstrip()
        else:
            self.name = name
            self.year = None

        #print('y={} n={}'.format(self.year, self.name))
        self.url = url
        self.args = urlparse.parse_qs(urlparse.urlparse(url).query)
        self.children = []


    @property
    def tab(self):
        if 'tab' in self.args:
            return self.args['tab'][0]

    @property
    def is_show(self):
        t = self.tab
        return t == 's'

    @property
    def is_most_recent(self):
        t = self.tab
        return t == 'm'

    @property
    def is_new(self):
        t = self.tab
        return not t

    @property
    def year(self):
        if self.year:
            return self.year

        if 'y' in self.args:
            return int(self.args['y'][0])

    @property
    def is_tournament(self):
        t = self.tab
        return t == 't'

    def load(self):
        def keep_text(s):
            if s.lower().startswith('reveal'):
                return False
            return True


        def is_p_with_head_title_class(tag):
            if tag.name != 'p':
                return False

            cl = tag.get('class') or []
            return len(cl) == 1 and cl[0] == 'head_title'

        def is_date(str):
            try:
                date = parse_datetime(str)
                return True
            except Exception as e:
                return False


        soup = get_bs(self.url)
        headings = soup.find_all(is_p_with_head_title_class)

        children = []
        for heading in headings:
            texts = cleanup_html_strings(heading.stripped_strings)
            name = u' '.join(texts)
            sibling = heading.next_sibling
            if sibling:
                table = sibling.parent
                if table and table.name == 'table':
                    g2 = Grouping(name)
                    for row in table.find_all('tr'):
                        texts = cleanup_html_strings(row.stripped_strings)
                        texts = filter(keep_text, texts)
                        dates = filter(is_date, texts)

                        date = None
                        if len(dates):
                            date = parse_datetime(dates[0])
                            texts.remove(dates[0])

                        href = row.find('a')['href']
                        title = texts[0]
                        extra = u' '.join(texts[1:])

                        g2.videos.append(Video(href, title, date, extra))

                    children.append(g2)

        self.children = children


class Sc2Links:
    # cat=S / tab=s -> show
    # cat=T -> tournament
    # tab=t
    # tab=m -> most recent y=yyyy
    DOMAIN = 'https://sc2links.com'

    def __init__(self):
        self.__links = []
        self.__years = []

    def load(self):
        # collect links
        self.__links = []
        self.__years = None

        soup = get_bs(Sc2Links.DOMAIN + '/tournament.php')
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and href.startswith('tournament.php?'):
                texts = cleanup_html_strings(link.stripped_strings)
                name = u' '.join(texts)
                self.__links.append(Collection(name, Sc2Links.DOMAIN + '/' + href))


    def shows(self, **kwargs):
        links = [link for link in self.__links if link.is_show]
        if 'year' in kwargs:
            links = [link for link in links if link.year == str(kwargs['year'])]
        return links

    def tournaments(self, **kwargs):
        links = [link for link in self.__links if link.is_tournament]
        if 'year' in kwargs:
            links = [link for link in links if link.year == str(kwargs['year'])]
        return links

    def most_recent(self, **kwargs):
        links = [link for link in self.__links if link.is_most_recent]
        if 'year' in kwargs:
            links = [link for link in links if link.year == str(kwargs['year'])]
        return links

    @property
    def new(self):
        return [link for link in self.__links if link.is_new]

    @property
    def years(self):
        # lazy get years
        if not self.__years:
            self.__years = self.__make_years()

        return self.__years

    def __make_years(self):
        ys = []
        for link in self.__links:
            y = link.year
            if y:
                intY = int(y)
                if not intY in ys:
                    ys.append(intY)

        ys.sort(key=lambda x: x, reverse=True)
        return ys
