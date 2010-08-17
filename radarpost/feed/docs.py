from couchdb.http import ResourceConflict, ResourceNotFound
from couchdb.mapping import *
from hashlib import md5
from radarpost.mailbox import Message, Subscription

__all__ = ['FEED_SUBSCRIPTION_TYPE', 'BASIC_NEWS_ITEM_TYPE', 'BasicNewsItem', 'FeedSubscription']

FEED_SUBSCRIPTION_TYPE = 'feed'
BASIC_NEWS_ITEM_TYPE = 'basic_news_item'

# document subclasses for news feeds 
# used inside a mailbox

class BasicNewsItem(Message):
    """
    Represents a general RSS news item
    from a feed as delivered to a Mailbox.
    """
    message_type = TextField(default=BASIC_NEWS_ITEM_TYPE)
    
    item_id = TextField()
    title = TextField()
    author = TextField()
    link = TextField()
    content = TextField()

class FeedSubscription(Subscription):
    """
    Represents a subscription of a mailbox to a particular 
    remote rss/atom/etc feed
    """
    subscription_type = TextField(default=FEED_SUBSCRIPTION_TYPE)

    url = TextField()
    last_ids = ListField(TextField)

