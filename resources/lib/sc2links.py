from bs4 import BeautifulSoup
import requests
import urlparse

def get_bs(url):
    r = requests.get(url)
    if not r.ok:
        raise IOError('Failed to get {}, code {}'.format(url, r.status_code))

    return BeautifulSoup(r.content, 'html.parser')


class Video:
    def __init__(self, parent, url, name, date, extra):
        self.parent = parent
        self.url = url
        self.name = name
        self.date = date
        self.extra = extra


class Grouping:
    def __init__(self, parent, name, videos=None):
        self.parent = parent
        self.name = name
        self.videos = videos or []


class Collection:
    def __init__(self, name, url):
        self.name = name
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
        if 'y' in self.args:
            return self.args['y'][0]

    @property
    def is_tournament(self):
        t = self.tab
        return t == 't'

    def load(self):
        def keep_text(s):
            if not s:
                return False
            if s.lower().startswith('reveal'):
                return False
            return True


        def is_p_with_head_title_class(tag):
            if tag.name != 'p':
                return False

            cl = tag.get('class') or []
            return len(cl) == 1 and cl[0] == 'head_title'

        soup = get_bs(self.url)
        headings = soup.find_all(is_p_with_head_title_class)

        children = []
        for heading in headings:
            name = ' '.join(heading.stripped_strings)
            sibling = heading.next_sibling
            if sibling:
                table = sibling.parent
                if table and table.name == 'table':
                    g2 = Grouping(self, name)
                    for row in table.find_all('tr'):
                        texts = filter(keep_text, row.stripped_strings)
                        href = row.find('a')['href']
                        episode = texts[0]
                        date = texts[1]
                        extra = ' '.join(texts[2:])

                        g2.videos.append(Video(g2, href, episode, date, extra))

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
                name = ' '.join(link.stripped_strings)
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
