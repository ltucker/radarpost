import json
from xml.etree import ElementTree as etree
from radarpost.mailbox import is_mailbox
from radarpost.web.context import get_couchdb_server, get_database_name
from radarpost.web.context import get_mailbox, get_mailbox_slug
from radarpost.web.tests import RadarTestCase

class TestMailboxREST(RadarTestCase):

    def test_mailbox_create(self):
        """
        test creating a mailbox
        """
        try:
            slug = self.TEST_MAILBOX_SLUG + '_test_mailbox_create'
            mb_url = self.url_for('mailbox_rest', mailbox_slug=slug)
            assert get_mailbox(self.config, slug) is None
            
            c = self.get_test_app()
            c.head(mb_url, status=404)
            c.post(mb_url, '{}', content_type="application/json", status=201)
            c.head(mb_url, status=200)

            
            mb = get_mailbox(self.config, slug)
            assert mb is not None
            assert is_mailbox(mb)
        finally:
            dbname = get_database_name(self.config, slug)
            couchdb = get_couchdb_server(self.config)
            if dbname in couchdb: 
                del couchdb[dbname]
                
    def test_mailbox_delete(self):
        """
        test deleting a mailbox
        """
        mb = self.create_test_mailbox()
        slug = get_mailbox_slug(self.config, mb.name)
        mb_url = self.url_for('mailbox_rest', mailbox_slug=slug)
        c = self.get_test_app()
        c.head(mb_url, status=200)
        c.delete(mb_url, status=200)
        c.head(mb_url, status=404)
        c.delete(mb_url, status=404)

    def test_mailbox_head(self):
        """
        tests using head request to check mailbox
        existence.
        """
        slug = self.TEST_MAILBOX_SLUG
        mb_url = self.url_for('mailbox_rest', mailbox_slug=slug)
        c = self.get_test_app()
        c.head(mb_url, status=404)
        mb = self.create_test_mailbox(slug)
        c.head(mb_url, status=200)


class TestAtomFeeds(RadarTestCase):
    
    def test_atom_feed_exists(self):
        from radarpost.feed import parse as parse_feed
        
        slug = self.TEST_MAILBOX_SLUG
        feed_url = self.url_for('atom_feed', mailbox_slug=slug)
        c = self.get_test_app()
        c.get(feed_url, status=404)
        mb = self.create_test_mailbox(slug)
        response = c.get(feed_url, status=200)
        
        # body should parse as a feed
        ff = parse_feed(response.body, feed_url)
        assert len(ff.entries) == 0
        
    def test_atom_feed_entries_ordered(self):
        from datetime import datetime, timedelta
        from radarpost.feed import parse as parse_feed, BasicNewsItem, \
            FeedSubscription, create_basic_news_item
        from random import shuffle
        
        c = self.get_test_app()
        slug = self.TEST_MAILBOX_SLUG
        mb = self.create_test_mailbox(slug)
        feed_url = self.url_for('atom_feed', mailbox_slug=slug)

        # there should currently be an empty feed 
        response = c.get(feed_url, status=200)
        ff = parse_feed(response.body, feed_url)
        assert len(ff.entries) == 0
        
        # now put some items in the mailbox 
        # by hand.
        items = []
        base_date = datetime(1999, 12, 29, 0)
        delta = timedelta(seconds=10)
        for i in range(10):
            item_id = 'TestItem%d' % i
            item = BasicNewsItem(
                fingerprint = item_id,
                item_id = item_id,
                timestamp = base_date + i*delta,
                title = 'Test Item %d' % i,
                author = 'Joe',
                link = 'http://www.example.org/%d' % i,
                content = "Blah Blah %d" % i,
            )
            items.append(item)
        items.reverse() # order from newest to oldest
    
        # store them in a random order
        shuffled = list(items)
        shuffle(shuffled)
        for item in shuffled:
            item.store(mb)
    
        response = c.get(feed_url, status=200)
        ff = parse_feed(response.body, feed_url)
        assert len(ff.entries) == len(items)
        
        fake_sub = FeedSubscription(url=feed_url)
        for i, item in enumerate(items):
            ent = create_basic_news_item(ff.entries[i], ff, fake_sub)
            #assert ent.item_id == item.item_id
            assert ent.timestamp == item.timestamp
            assert ent.author == item.author
            assert ent.link == item.link
            assert ent.content == item.content
        

class TestOPML(RadarTestCase):
    
    def test_opml_empty_get(self):
        mb = self.create_test_mailbox()
        slug = get_mailbox_slug(self.config, mb.name)
        c = self.get_test_app()
        opml_url = self.url_for('feeds_opml', mailbox_slug=slug)
        response = c.get(opml_url, status=200)
        feeds = feeds_in_opml(response.body)
        
        assert len(feeds.keys()) == 0

    def test_post_bad_opml(self):
        mb = self.create_test_mailbox()
        slug = get_mailbox_slug(self.config, mb.name)
        c = self.get_test_app()
        opml_url = self.url_for('feeds_opml', mailbox_slug=slug)
        opml = "this ain't opml"
        c.post(opml_url, opml, content_type='text/xml', status=400)

    def test_put_bad_opml(self):
        mb = self.create_test_mailbox()
        slug = get_mailbox_slug(self.config, mb.name)
        c = self.get_test_app()
        opml_url = self.url_for('feeds_opml', mailbox_slug=slug)
        opml = "this ain't opml"
        c.put(opml_url, opml, content_type='text/xml', status=400)


    def test_opml_post(self):
        mb = self.create_test_mailbox()
        slug = get_mailbox_slug(self.config, mb.name)
        c = self.get_test_app()
        
        opml_url = self.url_for('feeds_opml', mailbox_slug=slug)
    
        feeds = {'http://www.example.org/feeds/1': 'feed 1',
                 'http://www.example.org/feeds/2': 'feed 2',
                 'http://www.example.org/feeds/3': 'feed 3'
                 }
        opml = make_opml(feeds)
        response = c.post(opml_url, opml, content_type='text/xml', status=200)
        info = json.loads(response.body)
        assert info['errors'] == 0
        assert info['deleted'] == 0
        assert info['imported'] == 3

        response = c.get(opml_url, status=200)
        out_feeds = feeds_in_opml(response.body)
        
        for url, title in out_feeds.items():
            assert url in feeds
            assert feeds[url] == title
            
        for url, title in feeds.items():
            assert url in out_feeds
            assert out_feeds[url] == title
        
    def test_opml_post_appends(self):
        from radarpost.feed import FeedSubscription
        
        mb = self.create_test_mailbox()
        slug = get_mailbox_slug(self.config, mb.name)
        c = self.get_test_app()
        
        opml_url = self.url_for('feeds_opml', mailbox_slug=slug)
    
        feeds1 = {'http://www.example.org/feeds/1': 'feed 1',
                 'http://www.example.org/feeds/2': 'feed 2',
                 'http://www.example.org/feeds/3': 'feed 3'
                 }
        opml = make_opml(feeds1)
        c.post(opml_url, opml, content_type='text/xml', status=200)

        feeds2 = {'http://www.example.org/feeds/3': 'feed 3',
                 'http://www.example.org/feeds/4': 'feed 4',
                 'http://www.example.org/feeds/5': 'feed 5'
                 }
        opml = make_opml(feeds2)
        response = c.post(opml_url, opml, content_type='text/xml', status=200)
        info = json.loads(response.body)
        assert info['errors'] == 0
        assert info['deleted'] == 0
        assert info['imported'] == 2

        response = c.get(opml_url, status=200)
        out_feeds = feeds_in_opml(response.body)
        
        all_feeds = {}
        all_feeds.update(feeds1)
        all_feeds.update(feeds2) 
        
        for url, title in out_feeds.items():
            assert url in all_feeds
            assert all_feeds[url] == title
            
        for url, title in all_feeds.items():
            assert url in out_feeds
            assert out_feeds[url] == title
            
        count = 0
        for r in mb.view(FeedSubscription.by_url):
            count += 1
        assert count == 5

    def test_opml_put(self):
        mb = self.create_test_mailbox()
        slug = get_mailbox_slug(self.config, mb.name)
        c = self.get_test_app()
        
        opml_url = self.url_for('feeds_opml', mailbox_slug=slug)
    
        feeds = {'http://www.example.org/feeds/1': 'feed 1',
                 'http://www.example.org/feeds/2': 'feed 2',
                 'http://www.example.org/feeds/3': 'feed 3'
                 }
        opml = make_opml(feeds)
        response = c.put(opml_url, opml, content_type='text/xml', status=200)
        info = json.loads(response.body)
        assert info['errors'] == 0
        assert info['deleted'] == 0
        assert info['imported'] == 3

        response = c.get(opml_url, status=200)
        out_feeds = feeds_in_opml(response.body)
        
        for url, title in out_feeds.items():
            assert url in feeds
            assert feeds[url] == title
            
        for url, title in feeds.items():
            assert url in out_feeds
            assert out_feeds[url] == title

    def test_opml_put_overwrites(self):
        from radarpost.feed import FeedSubscription

        mb = self.create_test_mailbox()
        slug = get_mailbox_slug(self.config, mb.name)
        c = self.get_test_app()

        opml_url = self.url_for('feeds_opml', mailbox_slug=slug)

        feeds1 = {'http://www.example.org/feeds/1': 'feed 1',
                 'http://www.example.org/feeds/2': 'feed 2',
                 'http://www.example.org/feeds/3': 'feed 3'
                 }
        opml = make_opml(feeds1)
        c.put(opml_url, opml, content_type='text/xml', status=200)

        feeds2 = {'http://www.example.org/feeds/3': 'feed 3',
                 'http://www.example.org/feeds/4': 'feed 4',
                 'http://www.example.org/feeds/5': 'feed 5'
                 }
        opml = make_opml(feeds2)
        response = c.put(opml_url, opml, content_type='text/xml', status=200)
        info = json.loads(response.body)
        assert info['errors'] == 0
        assert info['deleted'] == 2
        assert info['imported'] == 2

        response = c.get(opml_url, status=200)
        out_feeds = feeds_in_opml(response.body)
        
        for url, title in feeds2.items():
            assert url in feeds2
            assert feeds2[url] == title
            
        for url, title in feeds2.items():
            assert url in out_feeds
            assert out_feeds[url] == title

        count = 0
        for r in mb.view(FeedSubscription.by_url):
            count += 1
        assert count == 3


def feeds_in_opml(opml_data):
    opml = etree.XML(opml_data)
    feeds = {}
    #for node in opml.xpath('//outline[@type="rss"]'):
    for node in opml.getiterator('outline'):
        if node.get('type', '').lower() == 'rss':
            url= node.get('xmlUrl', None)
            if url is not None:
                feeds[url] = node.get('title', '')
    return feeds

def make_opml(feeds):
    opml = '<opml version="1.0"><head/><body>'
    for feed, title in feeds.items():
        opml += '<outline type="rss" xmlUrl="%s" title="%s" />' % (feed, title)
    opml += '</body></opml>'
    return opml

