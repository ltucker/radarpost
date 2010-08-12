import cgi
from datetime import datetime
import feedparser
import re

def parse(content, url):
    """
    produces a python representation of the RSS feed content 
    given. This representation is documented at: 
    http://feedparser.org
    
    content - string containing RSS/atom/etc xml document
    url - the url that the content was retrieved from.

    raises: InvalidFeedError if no feed could be parse.
    """
    
    fake_headers = {
        'content-location': url,
        'content-type': 'text/xml; charset=utf-8',
    }
    ff = feedparser.parse(content, header_defaults=fake_headers)

    if ff is None or not 'feed' in ff:
        raise InvalidFeedError()


    # make sure the feed has an id...
    if not 'id' in ff.feed:
        ff.feed['id'] = url

    # make sure the feed has a self referential link
    has_self_ref = False
    ff.feed.setdefault('links', [])
    for link in ff.feed.links:
        if link.rel == 'self':
            has_self_ref = True
            break
    if not has_self_ref:
        ff.feed.links.append(FakeLink(rel='self', href=url, title=''))

    for e in ff.get('entries', []):
        # make sure it has an id
        eid = e.get('id', None)
        if eid is None:
            eid = find_best_entry_id(e)
            if eid is None:
                # throw this entry out, it has no 
                # id, title, summary or content
                # that is recognizable...
                continue
            e['id'] = eid

    return ff

class FakeLink(object): 
    def __init__(sefl, rel, href, title): 
        self.rel = rel
        self.href = href
        self.title = title

def find_best_entry_id(entry):
    if entry.has_key('id'):
        return entry['id']
    elif entry.has_key('link') and entry['link']:
        return entry['link']
    elif entry.has_key('title') and entry['title']:
        return (entry.title_detail.base + "/" +
                md5(entry['title']).hexdigest())
    elif entry.has_key('summary') and entry['summary']:
        return (entry['summary_detail']['base'] + "/" +
                md5(entry['summary']).hexdigest())
    elif entry.has_key("content") and entry['content']:
        return (entry['content'][0]['base'] + "/" + 
                md5(entry['content'][0]['value']).hexdigest())
    else:
        return None


def find_best_timestamp(thing, default=None):
    """
    return the latest timestamp specified as a datetime. 
    timestamps are returned in this preference order: 
    updated, published, created
    """
    ts = thing.get('updated_parsed', None)
    if ts is None:
        ts = thing.get('published_parsed', None)
    if ts is None:
        ts = thing.get('created_parsed', None)

    if ts is not None:
        return datetime(*ts[0:6])
    else:
        return default

def find_best_permalink(entry, default=''):
    links = entry.get('links', [])
    for link in links:
        rel = link.get('rel', '')
        href = link.get('href', '')
        if href and rel and rel == 'alternate':
            return href
    return default

def find_author_name(entry, default=''):
    if 'author_detail' in entry and 'name' in entry.author_detail and entry.author_detail.name:
        return entry.author_detail.name
    elif 'author' in entry and entry.author:
        return cgi.escape(entry.author)
    else:
        return default

def find_source_url(e, default=''):
    links = e.get('links', [])
    for link in links:
        rel = link.get('rel', '')
        href = link.get('href', '')
        if href and rel and rel == 'self':
            return href
    return default


HTML_TYPES = ['text/html', 'application/xhtml+xml']
def as_html(content):
    if content is None:
        return ''
    if content.type in HTML_TYPES:
        return content.value
    else:
        return cgi.escape(content.value)

def stripped_content(content, maxlen=None):
    """
    return the content node given stripped of
    html tags and length limited as specified.

    if the content is longer than maxlen, the 
    string is truncated and the final three
    characters of the truncated string are
    replaced with ...
    """
    if content is None:
        return ''

    if content.type in HTML_TYPES:
        try:
            outstr = strip_tags(content.value)
        except:
            # didn't parse, just escape it (gigo)... 
            outstr = cgi.escape(content.value)
    else:
        outstr = cgi.escape(content.value)

    if maxlen:
        return trimmed(outstr, maxlen)
    else:
        return outstr

def trimmed(text, maxlen):
    if text is None:
        return ''
    if len(text) > maxlen:
        return text[0:maxlen-3] + '...'
    else:
        return text

import HTMLParser
class MLStripper(HTMLParser.HTMLParser):
    def __init__(self):
        self.reset()
        self._text = []
    def handle_data(self, d):
        self._text.append(d)
    def handle_charref(self, name):
        self._text.append('&#%s;' % name)
    def handle_entityref(self, name):
        self._text.append('&%s;' % name)

    @property
    def text(self):
        text = ''
        for chunk in self._text:
            if not chunk:
                continue
            if chunk.startswith(' '):
                text += re.sub('^\s+', ' ', chunk)
            else:
                text += chunk
            text.strip()
        return text

def strip_tags(html):
    stripper = MLStripper()
    stripper.feed(html)
    return stripper.text
