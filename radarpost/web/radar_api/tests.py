from couchdb import Server, PreconditionFailed
from django.core.urlresolvers import reverse as urlfor
from django.test.client import Client
import json
from unittest import TestCase
from xml.etree import ElementTree as etree
from radarpost.mailbox import create_mailbox as _create_mailbox, is_mailbox
from radarpost.web.helpers import get_mailbox, get_database_name, get_mailbox_slug, get_couchdb_server

class RadarTestCase(TestCase):

    def tearDown(self):
        couchdb = get_couchdb_server()
        dbname = get_database_name(TEST_MAILBOX_SLUG)
        if dbname in couchdb:
            del couchdb[dbname]


class TestMailboxREST(RadarTestCase):

    def test_mailbox_create(self):
        """
        test creating a mailbox
        """
        try:
            slug = TEST_MAILBOX_SLUG + '_test_mailbox_create'
            mb_url = urlfor('mailbox_rest', args=(slug,))
            assert get_mailbox(slug) is None
            
            c = Client()
            response = c.head(mb_url)
            assert response.status_code == 404
            response = c.post(mb_url, '{}', content_type="application/json")
            assert response.status_code == 201
            response = c.head(mb_url)
            assert response.status_code == 200
            
            mb = get_mailbox(slug)
            assert mb is not None
            assert is_mailbox(mb)
        finally:
            dbname = get_database_name(slug)
            couchdb = get_couchdb_server()
            if dbname in couchdb: 
                del couchdb[dbname]
                
    def test_mailbox_delete(self):
        """
        test deleting a mailbox
        """
        mb = create_test_mailbox()
        slug = get_mailbox_slug(mb.name)
        mb_url = urlfor('mailbox_rest', args=(slug,))
        c = Client()
        response = c.head(mb_url)
        assert response.status_code == 200
        response = c.delete(mb_url)
        assert response.status_code == 200
        response = c.head(mb_url)
        assert response.status_code == 404
        response = c.delete(mb_url)
        assert response.status_code == 404


class TestOPML(RadarTestCase):
    
    def test_opml_empty_get(self):
        mb = create_test_mailbox()
        slug = get_mailbox_slug(mb.name)
        c = Client()
        opml_url = urlfor('feeds_opml', args=(slug,))
        response = c.get(opml_url)
    
        assert response.status_code == 200
        feeds = feeds_in_opml(response.content)
        
        assert len(feeds.keys()) == 0

    def test_post_bad_opml(self):
        mb = create_test_mailbox()
        slug = get_mailbox_slug(mb.name)
        c = Client()
        opml_url = urlfor('feeds_opml', args=(slug,))
        opml = "this ain't opml"
        response = c.post(opml_url, data=opml, content_type='text/xml')
        assert response.status_code == 400

    def test_put_bad_opml(self):
        mb = create_test_mailbox()
        slug = get_mailbox_slug(mb.name)
        c = Client()
        opml_url = urlfor('feeds_opml', args=(slug,))
        opml = "this ain't opml"
        response = c.put(opml_url, data=opml, content_type='text/xml')
        assert response.status_code == 400


    def test_opml_post(self):
        mb = create_test_mailbox()
        slug = get_mailbox_slug(mb.name)
        c = Client()
        
        opml_url = urlfor('feeds_opml', args=(slug,))
    
        feeds = {'http://www.example.org/feeds/1': 'feed 1',
                 'http://www.example.org/feeds/2': 'feed 2',
                 'http://www.example.org/feeds/3': 'feed 3'
                 }
        opml = make_opml(feeds)
        response = c.post(opml_url, data=opml, content_type='text/xml')

        assert response.status_code == 200

        info = json.loads(response.content)
        assert info['errors'] == 0
        assert info['deleted'] == 0
        assert info['imported'] == 3

        response = c.get(opml_url)
        assert response.status_code == 200
        out_feeds = feeds_in_opml(response.content)
        
        for url, title in out_feeds.items():
            assert url in feeds
            assert feeds[url] == title
            
        for url, title in feeds.items():
            assert url in out_feeds
            assert out_feeds[url] == title
        
    def test_opml_post_appends(self):
        from radarpost.feed import FeedSubscription
        
        mb = create_test_mailbox()
        slug = get_mailbox_slug(mb.name)
        c = Client()
        
        opml_url = urlfor('feeds_opml', args=(slug,))
    
        feeds1 = {'http://www.example.org/feeds/1': 'feed 1',
                 'http://www.example.org/feeds/2': 'feed 2',
                 'http://www.example.org/feeds/3': 'feed 3'
                 }
        opml = make_opml(feeds1)
        response = c.post(opml_url, data=opml, content_type='text/xml')
        assert response.status_code == 200

        feeds2 = {'http://www.example.org/feeds/3': 'feed 3',
                 'http://www.example.org/feeds/4': 'feed 4',
                 'http://www.example.org/feeds/5': 'feed 5'
                 }
        opml = make_opml(feeds2)
        response = c.post(opml_url, data=opml, content_type='text/xml')
        assert response.status_code == 200

        info = json.loads(response.content)
        assert info['errors'] == 0
        assert info['deleted'] == 0
        assert info['imported'] == 2

        response = c.get(opml_url)
        assert response.status_code == 200
        out_feeds = feeds_in_opml(response.content)
        
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
        mb = create_test_mailbox()
        slug = get_mailbox_slug(mb.name)
        c = Client()
        
        opml_url = urlfor('feeds_opml', args=(slug,))
    
        feeds = {'http://www.example.org/feeds/1': 'feed 1',
                 'http://www.example.org/feeds/2': 'feed 2',
                 'http://www.example.org/feeds/3': 'feed 3'
                 }
        opml = make_opml(feeds)
        response = c.put(opml_url, data=opml, content_type='text/xml')
        assert response.status_code == 200

        info = json.loads(response.content)
        assert info['errors'] == 0
        assert info['deleted'] == 0
        assert info['imported'] == 3

        response = c.get(opml_url)
        assert response.status_code == 200
        out_feeds = feeds_in_opml(response.content)
        
        for url, title in out_feeds.items():
            assert url in feeds
            assert feeds[url] == title
            
        for url, title in feeds.items():
            assert url in out_feeds
            assert out_feeds[url] == title

    def test_opml_put_overwrites(self):
        from radarpost.feed import FeedSubscription

        mb = create_test_mailbox()
        slug = get_mailbox_slug(mb.name)
        c = Client()

        opml_url = urlfor('feeds_opml', args=(slug,))

        feeds1 = {'http://www.example.org/feeds/1': 'feed 1',
                 'http://www.example.org/feeds/2': 'feed 2',
                 'http://www.example.org/feeds/3': 'feed 3'
                 }
        opml = make_opml(feeds1)
        response = c.put(opml_url, data=opml, content_type='text/xml')
        assert response.status_code == 200

        feeds2 = {'http://www.example.org/feeds/3': 'feed 3',
                 'http://www.example.org/feeds/4': 'feed 4',
                 'http://www.example.org/feeds/5': 'feed 5'
                 }
        opml = make_opml(feeds2)
        response = c.put(opml_url, data=opml, content_type='text/xml')
        assert response.status_code == 200

        info = json.loads(response.content)
        assert info['errors'] == 0
        assert info['deleted'] == 2
        assert info['imported'] == 2

        response = c.get(opml_url)
        assert response.status_code == 200
        out_feeds = feeds_in_opml(response.content)
        
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

TEST_MAILBOX_SLUG = '__rp_test_mailbox'
def create_test_mailbox(slug=TEST_MAILBOX_SLUG):
    c = Client()
    mb_url = urlfor('mailbox_rest', args=(slug,))
    response = c.head(mb_url)
    if response.status_code != 404:
        response = c.delete(mb_url)
        assert response.status_code == 200
    response = c.post(mb_url, '{}', content_type="application/json")
    assert response.status_code == 201
    return get_mailbox(slug)


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
