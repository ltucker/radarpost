import cgi
from couchdb.http import ResourceConflict, ResourceNotFound
from couchdb.mapping import *
from datetime import datetime
from radarpost.lib import feedparser
from hashlib import md5
import re

from radarpost.mailbox import Message, SourceInfo, Subscription, DESIGN_DOC_PLUGIN
from radarpost import plugins

__all__ = ['FEED_SUBSCRIPTION_TYPE', 'BASICNEWSITEM_TYPE', 
           'BasicNewsItem', 'FeedSubscription', 'parse',
           'InvalidFeedError']

FEED_SUBSCRIPTION_TYPE = 'feed'
BASICNEWSITEM_TYPE = 'basic_news_item'

# document subclasses for news feeds 
# used inside a mailbox


class FeedSourceInfo(SourceInfo):
    self_link = TextField()
    alt_link = TextField()

class BasicNewsItem(Message):
    """
    Represents a general RSS news item
    from a feed as delivered to a Mailbox.
    """
    message_type = TextField(default=BASICNEWSITEM_TYPE)
    
    source = DictField(FeedSourceInfo)

    item_id = TextField()
    title = TextField()
    author = TextField()
    link = TextField()
    content = TextField()

    user_updatable = ('title', 'author', 'link', 'content')

@plugins.plugin(Message.SUBTYPE_PLUGIN)
def create_basicnewsitem(typename):
    if typename == BASICNEWSITEM_TYPE: 
        return BasicNewsItem()
    return None

class FeedSubscription(Subscription):
    """
    Represents a subscription of a mailbox to a particular 
    remote rss/atom/etc feed
    """
    subscription_type = TextField(default=FEED_SUBSCRIPTION_TYPE)

    url = TextField()
    last_ids = ListField(TextField)

    # digest of last fetched content
    last_digest = TextField()

    # helpful view constants
    by_url = '_design/feed/_view/feeds_by_url'

    user_updatable = Subscription.user_updatable + ('url', )

@plugins.plugin(Subscription.SUBTYPE_PLUGIN)
def create_feedsub(typename):
    if typename == FEED_SUBSCRIPTION_TYPE: 
        return FeedSubscription()
    return None


#####################################
#
# update helpers
#
#####################################

def create_basic_news_item(entry, feed, subscription, news_item=None):
    """
    extract the information needed to create a BasicNewsItem 
    from the feed entry given.
    """

    if news_item is None:
        news_item = BasicNewsItem()

    # the guid of a basic news item is the 
    # md5 digest of the item's id and the source's url.
    guid = md5()
    guid.update(entry.id)
    guid.update(subscription.url)
    guid = guid.hexdigest()

    news_item.id = guid
    news_item.item_id = entry.id
    news_item.timestamp = find_best_timestamp(entry) or datetime.utcnow()
    news_item.title = stripped_content(entry.get('title_detail', None), 128)
    news_item.author = trimmed(find_author_name(entry), 128)
    news_item.link = find_best_permalink(entry)

    news_item.source.subscription_id = subscription.id
    news_item.source.subscription_type = subscription.subscription_type
    news_item.source.title = subscription.title or \
                             stripped_content(feed.feed.get('title_detail', None), 128) or \
                             subscription.url[0:128]
    for link in feed.feed.get('links', []):
        if link.rel == 'alternate': 
            news_item.source.alt_link = link.href
        if link.rel == 'self': 
            news_item.source.self_link = link.href

    content = entry.get('content')
    if content is None or len(content) == 0: 
        content = entry.get('summary_detail', None)
    else:
        content = content[0]
    
    if content is not None:
        news_item.content = content.value

    # a basic news item's fingerprint is the md5 
    # digest of its utf-8 encoding.
    if news_item.content:
        fingerprint = md5()
        fingerprint.update(news_item.content.encode('utf-8'))
        fingerprint = fingerprint.hexdigest()
    else: 
        fingerprint = guid

    news_item.fingerprint = fingerprint

    return news_item


def update_feed_subscription(mailbox, subscription, feed, full_update=True,
                             message_processor=create_basic_news_item,
                             message_filter=None,
                             subscription_delta=None):
    """
    updates a single subscription in a single mailbox.
    returns - number of new items

    mailbox - the mailbox to update
    subscription - the subscription to update
    feed - the parsed current version of the feed
    full_update - whether this represents the full current 
        state of the feed or this is a partial 
        update.
    message_filter - a callable applied to each new message 
        returning a value indicating whether
        to accept the message.
    subscription_delta - if specified, the subscription is update()'d
        with this as an argument before being saved.
    """
    
    # if this is a full update, we will 
    # replace subscription.last_ids, otherwise
    # we just append to the list.
    if full_update == True:
        current_ids = []
    else: 
        current_ids = subscription.last_ids

    new_messages = []
    for entry in feed.entries:
        message = message_processor(entry, feed, subscription)

        if message is None:
            continue
        
        current_ids.append(message.id)
        # don't re-add things we saw last time around.
        if message.id in subscription.last_ids: 
            continue

        if (message_filter is not None and message_filter(message) == False):
            continue
    
        new_messages.append(message)

    new_message_count = 0
    for (success, doc_id, rev_ex) in mailbox.update(new_messages):
        if success == True:
            new_message_count += 1
            
        # N.B. conflicts are ignored. 
        # this could also be exposed, reported or logged
        # if needed at some point.
        elif not isinstance(rev_ex, ResourceConflict):
            raise

    # great, now update the subscription info.
    now = datetime.utcnow()

    # if we are the latest updater, put in our info.
    while(subscription.last_update is None or subscription.last_update < now):
        try:
            subscription.status = Subscription.STATUS_OK
            subscription.last_ids = current_ids
            subscription.last_update = now
            if subscription_delta is not None:
                for k,v in subscription_delta.items():
                    setattr(subscription, k, v)
            subscription.store(mailbox)
            break
        except ResourceConflict:
            # oops changed since we started, reload it.
            try:
                subscription = mailbox[subscription.id]
            except ResourceNotFound:
                # deleted from underneath us, bail out.
                break
    return new_message_count

#####################################
#
# Feed parsing, normalizing helpers 
#
#####################################

class InvalidFeedError(Exception): 
    pass

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
    def __init__(self, rel, href, title): 
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


DESIGN_DOC = {
    '_id': '_design/feed',
    'views': {
        'feeds_by_url': {
            'map':
                """
                function(doc) {
                    if (doc.type == 'subscription' && doc.subscription_type == 'feed') {
                        emit(doc.url, {'_rev': doc._rev});
                    }
                }
                """
        }
    },
    'filters': {
    }
}
plugins.register(DESIGN_DOC, DESIGN_DOC_PLUGIN)

ENTITIES = {
    'quot' : 34, 'amp' : 38, 'apos' : 39, 'lt' : 60, 'gt' : 62, 
    'quot' : 34, 'amp' : 38, 'apos' : 39, 'lt' : 60, 'gt' : 62, 'nbsp' : 160, 
    'iexcl' : 161, 'cent' : 162, 'pound' : 163, 'curren' : 164, 'yen' : 165, 'brvbar' : 166, 
    'sect' : 167, 'uml' : 168, 'copy' : 169, 'ordf' : 170, 'laquo' : 171, 'not' : 172, 
    'shy' : 173, 'reg' : 174, 'macr' : 175, 'deg' : 176, 'plusmn' : 177, 'sup2' : 178, 
    'sup3' : 179, 'acute' : 180, 'micro' : 181, 'para' : 182, 'middot' : 183, 'cedil' : 184, 
    'sup1' : 185, 'ordm' : 186, 'raquo' : 187, 'frac14' : 188, 'frac12' : 189, 'frac34' : 190, 
    'iquest' : 191, 'Agrave' : 192, 'Aacute' : 193, 'Acirc' : 194, 'Atilde' : 195, 'Auml' : 196, 
    'Aring' : 197, 'AElig' : 198, 'Ccedil' : 199, 'Egrave' : 200, 'Eacute' : 201, 'Ecirc' : 202, 
    'Euml' : 203, 'Igrave' : 204, 'Iacute' : 205, 'Icirc' : 206, 'Iuml' : 207, 'ETH' : 208, 
    'Ntilde' : 209, 'Ograve' : 210, 'Oacute' : 211, 'Ocirc' : 212, 'Otilde' : 213, 'Ouml' : 214, 
    'times' : 215, 'Oslash' : 216, 'Ugrave' : 217, 'Uacute' : 218, 'Ucirc' : 219, 'Uuml' : 220, 
    'Yacute' : 221, 'THORN' : 222, 'szlig' : 223, 'agrave' : 224, 'aacute' : 225, 'acirc' : 226, 
    'atilde' : 227, 'auml' : 228, 'aring' : 229, 'aelig' : 230, 'ccedil' : 231, 'egrave' : 232, 
    'eacute' : 233, 'ecirc' : 234, 'euml' : 235, 'igrave' : 236, 'iacute' : 237, 'icirc' : 238, 
    'iuml' : 239, 'eth' : 240, 'ntilde' : 241, 'ograve' : 242, 'oacute' : 243, 'ocirc' : 244, 
    'otilde' : 245, 'ouml' : 246, 'divide' : 247, 'oslash' : 248, 'ugrave' : 249, 'uacute' : 250, 
    'ucirc' : 251, 'uuml' : 252, 'yacute' : 253, 'thorn' : 254, 'yuml' : 255, 'OElig' : 338, 
    'oelig' : 339, 'Scaron' : 352, 'scaron' : 353, 'Yuml' : 376, 'fnof' : 402, 'circ' : 710, 
    'tilde' : 732, 'Alpha' : 913, 'Beta' : 914, 'Gamma' : 915, 'Delta' : 916, 'Epsilon' : 917, 
    'Zeta' : 918, 'Eta' : 919, 'Theta' : 920, 'Iota' : 921, 'Kappa' : 922, 'Lambda' : 923, 
    'Mu' : 924, 'Nu' : 925, 'Xi' : 926, 'Omicron' : 927, 'Pi' : 928, 'Rho' : 929, 
    'Sigma' : 931, 'Tau' : 932, 'Upsilon' : 933, 'Phi' : 934, 'Chi' : 935, 'Psi' : 936, 
    'Omega' : 937, 'alpha' : 945, 'beta' : 946, 'gamma' : 947, 'delta' : 948, 'epsilon' : 949, 
    'zeta' : 950, 'eta' : 951, 'theta' : 952, 'iota' : 953, 'kappa' : 954, 'lambda' : 955, 
    'mu' : 956, 'nu' : 957, 'xi' : 958, 'omicron' : 959, 'pi' : 960, 'rho' : 961, 
    'sigmaf' : 962, 'sigma' : 963, 'tau' : 964, 'upsilon' : 965, 'phi' : 966, 'chi' : 967, 
    'psi' : 968, 'omega' : 969, 'thetasym' : 977, 'upsih' : 978, 'piv' : 982, 'ensp' : 8194, 
    'emsp' : 8195, 'thinsp' : 8201, 'zwnj' : 8204, 'zwj' : 8205, 'lrm' : 8206, 'rlm' : 8207, 
    'ndash' : 8211, 'mdash' : 8212, 'lsquo' : 8216, 'rsquo' : 8217, 'sbquo' : 8218, 'ldquo' : 8220, 
    'rdquo' : 8221, 'bdquo' : 8222, 'dagger' : 8224, 'Dagger' : 8225, 'bull' : 8226, 'hellip' : 8230, 
    'permil' : 8240, 'prime' : 8242, 'Prime' : 8243, 'lsaquo' : 8249, 'rsaquo' : 8250, 'oline' : 8254, 
    'frasl' : 8260, 'euro' : 8364, 'image' : 8465, 'weierp' : 8472, 'real' : 8476, 'trade' : 8482, 
    'alefsym' : 8501, 'larr' : 8592, 'uarr' : 8593, 'rarr' : 8594, 'darr' : 8595, 'harr' : 8596, 
    'crarr' : 8629, 'lArr' : 8656, 'uArr' : 8657, 'rArr' : 8658, 'dArr' : 8659, 'hArr' : 8660, 
    'forall' : 8704, 'part' : 8706, 'exist' : 8707, 'empty' : 8709, 'nabla' : 8711, 'isin' : 8712, 
    'notin' : 8713, 'ni' : 8715, 'prod' : 8719, 'sum' : 8721, 'minus' : 8722, 'lowast' : 8727, 
    'radic' : 8730, 'prop' : 8733, 'infin' : 8734, 'ang' : 8736, 'and' : 8743, 'or' : 8744, 
    'cap' : 8745, 'cup' : 8746, 'int' : 8747, 'there4' : 8756, 'sim' : 8764, 'cong' : 8773, 
    'asymp' : 8776, 'ne' : 8800, 'equiv' : 8801, 'le' : 8804, 'ge' : 8805, 'sub' : 8834, 
    'sup' : 8835, 'nsub' : 8836, 'sube' : 8838, 'supe' : 8839, 'oplus' : 8853, 'otimes' : 8855, 
    'perp' : 8869, 'sdot' : 8901, 'lceil' : 8968, 'rceil' : 8969, 'lfloor' : 8970, 'rfloor' : 8971, 
    'lang' : 9001, 'rang' : 9002, 'loz' : 9674, 'spades' : 9824, 'clubs' : 9827, 'hearts' : 9829, 
    'diams' : 9830, 
}

import HTMLParser
class MLStripper(HTMLParser.HTMLParser):
    def __init__(self):
        self.reset()
        self._text = []
    def handle_data(self, d):
        self._text.append(d)
    def handle_charref(self, name):
        if name.startswith('x'): 
            base = 16
            name = name[1:]
        else: 
            base = 10
            
        try: 
            code = int(name, base=base)
            self._text.append(unichr(code))
        except: 
            pass # ignore it.

    def handle_entityref(self, name):
        if name in ENTITIES: 
            self._text.append(unichr(ENTITIES[name]))
        # just skip it otherwise.

    @property
    def text(self):
        text = u''
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
