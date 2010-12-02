from helpers import *

def test_feed_basic():
    """
    test_feed_basic

    create a mailbox
    subscribe to a feed
    update the subscription
    assert expected items are in the mailbox
    """
    from radarpost.feed import FeedSubscription, update_feed_subscription, parse, AtomEntry
    from radarpost.mailbox import Message


    # create a random feed
    ff, entries = random_feed_info_and_entries(10)
    feed_doc = create_atom_feed(ff, entries)
    url = ff['url']

    # create a mailbox 
    mb = create_test_mailbox()
    # make sure there are no items in the mailbox
    count = 0
    for r in mb.view(Message.by_timestamp, group=False):
        count += r.value
    assert count == 0

    # subscribe to our feed and update the subscription  
    sub = FeedSubscription(url=url)
    sub.store(mb)
    feed = parse(feed_doc, url)
    update_feed_subscription(mb, sub, feed)

    # check that each item in the random feed is in the 
    # mailbox and only items from the random feed are in there.
    seen_ids = []
    for ni in AtomEntry.view(mb, Message.by_timestamp, include_docs=True, reduce=False):
        seen_ids.append(ni.entry_id)
    
    expected_ids = set([e['id'] for e in entries])
    assert len(seen_ids) == len(entries)
    for iid in seen_ids:
        assert iid in expected_ids


def test_feed_update():
    """
    create a mailbox
    subscribe to a feed
    update the subscription
    assert expected items are in the mailbox
    add new items to feed
    update subscription
    assert expected items are in the mailbox
    assert that old items are not repeated
    """
    from radarpost.feed import FeedSubscription, update_feed_subscription, parse, AtomEntry
    from radarpost.mailbox import Message

    # create two versions of a random feed.
    # the second version with additional items. 
    ff, entries = random_feed_info_and_entries(20)
    url = ff['url']
    ff1 = dict(ff)
    ff2 = dict(ff)
    entries1 = entries[10:] # last 10 only
    entries2 = entries # all entries
    ff1['timestamp'] = entries2[0]['timestamp']
    feed_doc1 = create_atom_feed(ff1, entries1) 
    feed_doc2 = create_atom_feed(ff2, entries2)

    # create a mailbox 
    mb = create_test_mailbox()
    # make sure there are no items in the mailbox
    count = 0
    for r in mb.view(Message.by_timestamp, group=False):
        count += r.value
    assert count == 0

    # subscribe to our feed and update the subscription  
    sub = FeedSubscription(url=url)
    sub.store(mb)
    
    # update with the first feed (first 10 items only)
    feed = parse(feed_doc1, url)
    update_feed_subscription(mb, sub, feed)

    # check that each item in the feed is in the 
    # mailbox and only items from the feed are in there.
    seen_ids = []
    for ni in AtomEntry.view(mb, Message.by_timestamp,
                                 include_docs=True, reduce=False):
        seen_ids.append(ni.entry_id)

    expected_ids = set([e['id'] for e in entries1])
    assert len(seen_ids) == len(entries1)
    for iid in seen_ids:
        assert iid in expected_ids

    # now update with the whole set of items
    feed = parse(feed_doc2, url)
    update_feed_subscription(mb, sub, feed)
    
    # check that all items are now in the feed is in the 
    # mailbox and only items from the feed are in there 
    # and they're there exactly once.
    seen_ids = []
    for ni in AtomEntry.view(mb, Message.by_timestamp,
                             include_docs=True, reduce=False):
        seen_ids.append(ni.entry_id)

    expected_ids = set([e['id'] for e in entries2])
    assert len(seen_ids) == len(entries2)
    for iid in seen_ids:
        assert iid in expected_ids
        
def test_feed_delete_sticks():
    """
    make sure that an item deleted from a mailbox does not 
    reappear if it still exists in the source feed.
    """
    from radarpost.feed import FeedSubscription, update_feed_subscription, parse, AtomEntry
    from radarpost.mailbox import Message
    
    # create two versions of a random feed.
    # the second version with additional items. 
    ff, entries = random_feed_info_and_entries(20)
    url = ff['url']
    ff1 = dict(ff)
    ff2 = dict(ff)
    entries1 = entries[10:] # last 10 only
    entries2 = entries # all entries
    ff1['timestamp'] = entries2[0]['timestamp']
    feed_doc1 = create_atom_feed(ff1, entries1) 
    feed_doc2 = create_atom_feed(ff2, entries2)

    # create a mailbox 
    mb = create_test_mailbox()
    # make sure there are no items in the mailbox
    count = 0
    for r in mb.view(Message.by_timestamp, group=False):
        count += r.value
    assert count == 0

    # subscribe to our feed and update the subscription  
    sub = FeedSubscription(url=url)
    sub.store(mb)
    
    # update with the first feed (first 10 items only)
    feed = parse(feed_doc1, url)
    update_feed_subscription(mb, sub, feed)

    # check that each item in the feed is in the 
    # mailbox and only items from the feed are in there.
    seen_ids = []
    news_items = []
    for ni in AtomEntry.view(mb, Message.by_timestamp,
                             include_docs=True, reduce=False):
        seen_ids.append(ni.entry_id)
        news_items.append(ni)

    expected_ids = set([e['id'] for e in entries1])
    assert len(seen_ids) == len(entries1)
    for iid in seen_ids:
        assert iid in expected_ids


    # delete one of the items
    killed_item = news_items[0]
    del mb[killed_item.id]
    assert killed_item.id not in mb

    # update with the same info
    update_feed_subscription(mb, sub, feed)
    # item should not have reappeared
    assert killed_item.id not in mb

    # now update with the whole set of items
    feed = parse(feed_doc2, url)
    update_feed_subscription(mb, sub, feed)
    
    # item should not have reappeared.
    assert killed_item.id not in mb


    # check that all other expected items are now in the feed is in the 
    # mailbox and only items from the feed are in there 
    # and they're there exactly once.
    seen_ids = []
    for ni in AtomEntry.view(mb, Message.by_timestamp,
                             include_docs=True, reduce=False):
        seen_ids.append(ni.entry_id)

    expected_ids = set([e['id'] for e in entries2])
    expected_ids.remove(killed_item.entry_id)
    assert len(seen_ids) == len(expected_ids)
    for iid in seen_ids:
        assert iid in expected_ids

def test_feeds_design_doc():
    """
    tests that the feeds design document is 
    added to mailboxes.
    """
    
    # create a mailbox 
    mb = create_test_mailbox()

    from radarpost.feed import FeedSubscription    
    url = 'http://example.com/feed.xml'
    sub = FeedSubscription(url=url)
    sub.store(mb)
    
    # lookup by url
    for ss in mb.view(FeedSubscription.by_url, startkey=url, endkey=url):
        assert ss.id == sub.id

    
    