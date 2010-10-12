import cgi
from couchdb.http import ResourceConflict, ResourceNotFound
from couchdb.mapping import *
from datetime import datetime
import feedparser
from hashlib import md5
import re

from radarpost.mailbox import Message, Subscription, DESIGN_DOC_PLUGIN
from radarpost import plugins

__all__ = ['FEED_SUBSCRIPTION_TYPE', 'BASICNEWSITEM_TYPE', 
           'BasicNewsItem', 'FeedSubscription', 'parse',
           'InvalidFeedError']

FEED_SUBSCRIPTION_TYPE = 'feed'
BASICNEWSITEM_TYPE = 'basic_news_item'

# document subclasses for news feeds 
# used inside a mailbox

class BasicNewsItem(Message):
    """
    Represents a general RSS news item
    from a feed as delivered to a Mailbox.
    """
    message_type = TextField(default=BASICNEWSITEM_TYPE)
    
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

    new_messages = 0
    for entry in feed.entries:
        message = message_processor(entry, feed, subscription)

        if message is None:
            continue
        
        current_ids.append(message.id)
        # don't re-add things we saw last time around.
        if message.id in subscription.last_ids: 
            continue

        try:
            if (message_filter is None or 
                message_filter(message) == True):
                message.store(mailbox)
                new_messages += 1
        except ResourceConflict:
            # oops, we've already got it. 
            pass

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
    return new_messages

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