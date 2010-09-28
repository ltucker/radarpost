import json
from xml.etree import ElementTree as etree
from radarpost.mailbox import is_mailbox
from radarpost.user import User
from radarpost.web.context import get_couchdb_server, get_database_name
from radarpost.web.context import get_mailbox, get_mailbox_slug
from radarpost.web.tests import RadarTestCase

class TestUserAPI(RadarTestCase):
    
    def test_create_user_urlenc_post(self):
        """
        tests creating a user by POST'ing form-encoded parameters
        to /user
        """
        uname = 'joe'
        uid = 'org.couchdb.user:%s' % uname
        udb = self.create_users_database()

        create_url = self.url_for('create_user')

        assert not uid in udb
        c = self.get_test_app()
        c.post(create_url, {'username': uname}, status=201)
        assert uid in udb
        c.post(create_url, {'username': uname}, status=409)
        del udb[uid]
        
        # test passwords.
        password = 'bl0w'
        bad_pass = 'b0w1'
        # missing password 2
        c.post(create_url, {'username': uname, 'password': password}, status=400)
        assert uid not in udb
        
        # passwords don't match
        c.post(create_url, {'username': uname, 
                            'password': password, 
                            'password2': bad_pass}, status=400)
        assert uid not in udb
        
        # okay 
        c.post(create_url, {'username': uname, 
                            'password': password, 
                            'password2': password}, status=201)
        user = User.get_by_username(udb, uname)
        assert user.check_password(password)
        assert not user.check_password(bad_pass)
        
    def test_create_user_json_post(self):
        """
        tests creating a user by POST'ing json-encoded parameters
        to /user
        """
        uname = 'joe'
        uid = 'org.couchdb.user:%s' % uname
        udb = self.create_users_database()

        create_url = self.url_for('create_user')

        assert not uid in udb
        c = self.get_test_app()
        c.post(create_url, json.dumps({'username': uname}), content_type="application/x-json", status=201)
        assert uid in udb
        c.post(create_url, json.dumps({'username': uname}), content_type="application/x-json", status=409)
        del udb[uid]

        # test passwords.
        password = 'bl0w'
        bad_pass = 'b0w1'
        # missing password 2
        c.post(create_url, json.dumps({'username': uname, 'password': password}), 
               content_type="application/x-json", status=400)
        assert uid not in udb

        # passwords don't match
        c.post(create_url, json.dumps({'username': uname, 
                            'password': password, 
                            'password2': bad_pass}), 
                            content_type="application/x-json", status=400)
        assert uid not in udb

        # okay 
        c.post(create_url, json.dumps({'username': uname, 
                            'password': password, 
                            'password2': password}), 
                            content_type="application/x-json", status=201)
        user = User.get_by_username(udb, uname)
        assert user.check_password(password)
        assert not user.check_password(bad_pass)


    def test_create_user_urlenc_put(self):
        """
        tests creating a user by PUT'ing form-encoded parameters
        to /user/<username>
        """
        uname = 'joe'
        uid = 'org.couchdb.user:%s' % uname
        udb = self.create_users_database()

        create_url = self.url_for('user_rest', userid=uname)

        assert not uid in udb
        c = self.get_test_app()
        c.put(create_url, {}, content_type="application/x-www-form-urlencoded", status=201)
        assert uid in udb
        c.put(create_url, {}, content_type="application/x-www-form-urlencoded", status=409)
        del udb[uid]

        # test passwords.
        password = 'bl0w'
        bad_pass = 'b0w1'
        # missing password 2
        c.put(create_url, {'password': password}, 
              content_type="application/x-www-form-urlencoded",
              status=400)
        assert uid not in udb

        # passwords don't match
        c.put(create_url, {'password': password, 
                            'password2': bad_pass}, 
                            content_type="application/x-www-form-urlencoded",
                            status=400)
        assert uid not in udb

        # okay 
        c.put(create_url, {'password': password, 
                           'password2': password}, 
                           content_type="application/x-www-form-urlencoded",
                           status=201)

        user = User.get_by_username(udb, uname)
        assert user.check_password(password)
        assert not user.check_password(bad_pass)


    def test_create_user_json_put(self):
        """
        tests creating a user by PUT'ing json-encoded parameters
        to /user/<username>
        """
        uname = 'joe'
        uid = 'org.couchdb.user:%s' % uname
        udb = self.create_users_database()

        create_url = self.url_for('user_rest', userid=uname)

        assert not uid in udb
        c = self.get_test_app()
        c.put(create_url, json.dumps({}), 
              content_type="application/x-json", status=201)
        assert uid in udb
        c.put(create_url, json.dumps({}),
              content_type="application/x-json", status=409)
        del udb[uid]

        # test passwords.
        password = 'bl0w'
        bad_pass = 'b0w1'
        # missing password 2
        c.put(create_url, json.dumps({'password': password}), 
              content_type="application/x-json",
              status=400)
        assert uid not in udb

        # passwords don't match
        c.put(create_url, json.dumps({'password': password, 
                            'password2': bad_pass}), 
                            content_type="application/x-json",
                            status=400)
        assert uid not in udb

        # okay 
        c.put(create_url, json.dumps({'password': password, 
                           'password2': password}), 
                           content_type="application/x-json",
                           status=201)

        user = User.get_by_username(udb, uname)
        assert user.check_password(password)
        assert not user.check_password(bad_pass)

    
    def test_user_exists(self):
        uname = 'joe'
        udb = self.create_users_database()
        user_url = self.url_for('user_rest', userid=uname)

        c = self.get_test_app()
        c.head(user_url, status=404)

        user = User(username=uname)
        user.store(udb)

        c.head(user_url, status=200)    
    
    def test_login_urlenc(self):
        uname = 'joe'
        password = 'bl0w'
        badpw = 'lb0w'
        
        udb = self.create_users_database()
        user = User(username=uname, password=password)
        user.store(udb)

        login_url = self.url_for('login')
        logout_url = self.url_for('logout')
        
        c = self.get_test_app()
        
        # not logged in 
        res = c.get(self.url_for('current_user_info'))
        info = json.loads(res.body)
        assert info['is_anonymous'] == True
        assert info.get('userid', None) is None

        # bad login
        c.post(login_url, {'username': uname, 'password': badpw}, status=401)
        res = c.get(self.url_for('current_user_info'))
        info = json.loads(res.body)
        assert info['is_anonymous'] == True
        assert info.get('userid', None) is None
        
        # successfull login 
        c.post(login_url, {'username': uname, 'password': password}, status=200)
        res = c.get(self.url_for('current_user_info'))
        info = json.loads(res.body)
        assert info['is_anonymous'] == False
        assert info['userid'] == 'joe'
        
        # logout
        c.post(logout_url, status=200)
        res = c.get(self.url_for('current_user_info'))
        info = json.loads(res.body)
        assert info['is_anonymous'] == True
        assert info.get('userid', None) is None

    def test_login_json(self):
        uname = 'joe'
        password = 'bl0w'
        badpw = 'lb0w'

        udb = self.create_users_database()
        user = User(username=uname, password=password)
        user.store(udb)

        login_url = self.url_for('login')
        logout_url = self.url_for('logout')

        c = self.get_test_app()

        # not logged in 
        res = c.get(self.url_for('current_user_info'))
        info = json.loads(res.body)
        assert info['is_anonymous'] == True
        assert info.get('userid', None) is None
        
        # bad login 
        c.post(login_url, json.dumps({'username': uname, 'password': badpw}), 
               content_type="application/x-json", status=401)
        res = c.get(self.url_for('current_user_info'))
        info = json.loads(res.body)
        assert info['is_anonymous'] == True
        assert info.get('userid', None) is None

        # successfull login
        c.post(login_url, json.dumps({'username': uname, 'password': password}), 
               content_type="application/x-json", status=200)
        res = c.get(self.url_for('current_user_info'))
        info = json.loads(res.body)
        assert info['is_anonymous'] == False
        assert info['userid'] == 'joe'

        # logout
        c.post(logout_url, status=200)
        res = c.get(self.url_for('current_user_info'))
        info = json.loads(res.body)
        assert info['is_anonymous'] == True
        assert info.get('userid', None) is None

    def test_delete_user(self):
        uname = 'joe'
        udb = self.create_users_database()
        user_url = self.url_for('user_rest', userid=uname)
        user = User(username=uname)
        user.store(udb)

        c = self.get_test_app()
        c.head(user_url, status=200)
        c.delete(user_url, status=200)
        c.head(user_url, status=404)
        c.delete(user_url, status=404)

    def test_update_user_passwd_post_json(self):
        uname = 'joe'
        pw1 = 'bl0w'
        pw2 = 'b0w1'
        udb = self.create_users_database()
        user_url = self.url_for('user_rest', userid=uname)
        c = self.get_test_app()
        c.post(user_url, '', status=404)
    
        user = User(username=uname, password=pw1)
        user.store(udb)
        
        user = User.get_by_username(udb, uname)
        assert user.check_password(pw1)
        assert not user.check_password(pw2)

        # missing password2
        c.post(user_url, json.dumps({'username': uname, 'password': pw2}), 
               content_type="application/x-json", status=400)
        user = User.get_by_username(udb, uname)
        assert user.check_password(pw1)
        assert not user.check_password(pw2)

        # passwords don't match
        c.post(user_url, json.dumps({'username': uname, 
                            'password': pw2, 
                            'password2': pw1}), 
                            content_type="application/x-json", status=400)
        user = User.get_by_username(udb, uname)
        assert user.check_password(pw1)
        assert not user.check_password(pw2)


        # okay 
        c.post(user_url, json.dumps({'username': uname, 
                            'password': pw2, 
                            'password2': pw2}), 
                            content_type="application/x-json", status=200)
        user = User.get_by_username(udb, uname)
        assert user.check_password(pw2)
        assert not user.check_password(pw1)


    def test_update_user_passwd_post_urlenc(self):
        uname = 'joe'
        pw1 = 'bl0w'
        pw2 = 'b0w1'
        udb = self.create_users_database()
        user_url = self.url_for('user_rest', userid=uname)
        c = self.get_test_app()
        c.post(user_url, {}, status=404)

        user = User(username=uname, password=pw1)
        user.store(udb)

        user = User.get_by_username(udb, uname)
        assert user.check_password(pw1)
        assert not user.check_password(pw2)

        # missing password2
        c.post(user_url, {'username': uname, 'password': pw2}, 
                status=400)
        user = User.get_by_username(udb, uname)
        assert user.check_password(pw1)
        assert not user.check_password(pw2)

        # passwords don't match
        c.post(user_url, {'username': uname, 
                            'password': pw2, 
                            'password2': pw1}, 
                             status=400)
        user = User.get_by_username(udb, uname)
        assert user.check_password(pw1)
        assert not user.check_password(pw2)


        # okay 
        c.post(user_url, {'username': uname, 
                            'password': pw2, 
                            'password2': pw2}, 
                             status=200)
        user = User.get_by_username(udb, uname)
        assert user.check_password(pw2)
        assert not user.check_password(pw1)




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

