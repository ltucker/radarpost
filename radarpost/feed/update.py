from couchdb.http import ResourceConflict
from datetime import datetime
from hashlib import md5
from radarpost.feed.docs import BasicNewsItem
from radarpost.feed.parser import *



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

    content = entry.get('content', [None])[0].value
    if content is None:
        content = entry.get('summary_detail', None)
    if content:
        news_item.content = content

    # a basic news item's fingerprint is the md5 
    # digest of its utf-8 encoding.
    fingerprint = md5()
    fingerprint.update(news_item.content.encode('utf-8'))
    fingerprint = fingerprint.hexdigest()
    news_item.fingerprint = fingerprint

    return news_item


def update_feed_subscription(mailbox, subscription, feed, 
                             message_processor=create_basic_news_item,
                             full_update=True, 
                             message_filter=None):
    """
    updates a single subscription in a single mailbox.

    mailbox - the mailbox to update
    subscription - the subscription to update
    feed - the parsed current version of the feed
    full_update - whether this represents the full current 
                  state of the feed or this is a partial 
                  update.
    message_filter - a callable applied to each new message 
                     returning a value indicating whether
                     to accept the message.
    """
    
    # if this is a full update, we will 
    # replace subscription.last_ids, otherwise
    # we just append to the list.
    if full_update == True:
        current_ids = []
    else: 
        current_ids = subscription.last_ids

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
        except ResourceConflict:
            # oops, we've already got it. 
            pass
    
    # great, now update the subscription info.
    now = datetime.utcnow()
    # if we are the latest updater, put in our info.
    while(subscription.last_update is None or subscription.last_update < now):
        try:
            subscription.last_ids = current_ids
            subscription.last_update = now
            subscription.store(mailbox)
            break
        except ResourceConflict:
            # oops changed since we started, reload it.
            try:
                subscription = mailbox[subscription.id]
            except ResourceNotFound:
                # deleted from underneath us, bail out.
                break
