import base64
import json
from xml.etree import ElementTree as etree
from radarpost.mailbox import is_mailbox, MailboxInfo
from radarpost.user import User
from radarpost.web.context import get_couchdb_server, get_database_name
from radarpost.web.context import get_mailbox, get_mailbox_slug
from radarpost.web.tests import RadarTestCase

class TestSubscriptionAPI(RadarTestCase):
    
    def test_create_sub_post(self):
        """
        test create subscription by POST to <mbid>/subscriptions
        """
        url = 'http://example.com/feed/1'
        title = 'The Example Feed'
        
        mb = self.create_test_mailbox()
        slug =  get_mailbox_slug(self.config, mb.name)
        
        c = self.get_test_app()
        self.login_as_admin(c)

        subs_url = self.url_for('subscriptions_rest', mailbox_slug=slug)

        response = c.get(subs_url)
        all_subs = json.loads(response.body)
        
        assert len(all_subs) == 0
        
        info = {'type': 'feed', 'title': title, 'url': url}
        c.post(subs_url, json.dumps(info), content_type='application/json', status=201)

        response = c.get(subs_url)
        all_subs = json.loads(response.body)

        assert len(all_subs) == 1
        assert all_subs[0]['type'] == 'feed'
        assert all_subs[0]['title'] == title
        assert all_subs[0]['url'] == url
        
    def test_delete_sub(self):
        """
        test deleting a subscription by DELETE
        """
        
        url = 'http://example.com/feed/1'
        title = 'The Example Feed'

        url2 = 'http://example.com/feed/2'
        title2 = 'The Example Feed 2'

        mb = self.create_test_mailbox()
        slug =  get_mailbox_slug(self.config, mb.name)

        c = self.get_test_app()
        self.login_as_admin(c)

        subs_url = self.url_for('subscriptions_rest', mailbox_slug=slug)

        response = c.get(subs_url)
        all_subs = json.loads(response.body)
        assert len(all_subs) == 0
        
        # create two subscriptions
        info = {'type': 'feed', 'title': title, 'url': url}
        c.post(subs_url, json.dumps(info), content_type='application/json', status=201)
        
        info = {'type': 'feed', 'title': title2, 'url': url2}
        c.post(subs_url, json.dumps(info), content_type='application/json', status=201)

        response = c.get(subs_url)
        all_subs = json.loads(response.body)

        assert len(all_subs) == 2

        # delete the second subscription
        for sub in all_subs: 
            if sub['url'] == url2: 
                del_url = self.url_for('subscription_rest',
                                       mailbox_slug=slug,
                                       sub_slug=sub['slug'])
                c.delete(del_url)
        
        # check that the first subscription is the only thing there
        response = c.get(subs_url)
        all_subs = json.loads(response.body)
        assert len(all_subs) == 1
        assert all_subs[0]['type'] == 'feed'
        assert all_subs[0]['title'] == title
        assert all_subs[0]['url'] == url


    def test_sub_get(self):
        """
        test GET to subscription slug to retrieve info
        """
        
        url = 'http://example.com/feed/1'
        title = 'The Example Feed'

        mb = self.create_test_mailbox()
        slug =  get_mailbox_slug(self.config, mb.name)

        c = self.get_test_app()
        self.login_as_admin(c)

        subs_url = self.url_for('subscriptions_rest', mailbox_slug=slug)

        response = c.get(subs_url)
        all_subs = json.loads(response.body)
        assert len(all_subs) == 0

        info = {'type': 'feed', 'title': title, 'url': url}
        response = c.post(subs_url, json.dumps(info), content_type='application/json', status=201)
        sub_slug = json.loads(response.body)['slug']
        info_url = self.url_for('subscription_rest', mailbox_slug=slug, 
                                sub_slug=sub_slug)

        response = c.get(info_url)
        subinfo = json.loads(response.body)
        assert subinfo['type'] == 'feed'
        assert subinfo['title'] == title
        assert subinfo['url'] == url


    def test_sub_head(self):
        """
        test HEAD to check subscription existence
        """

        url = 'http://example.com/feed/1'
        title = 'The Example Feed'

        mb = self.create_test_mailbox()
        slug =  get_mailbox_slug(self.config, mb.name)

        c = self.get_test_app()
        self.login_as_admin(c)

        subs_url = self.url_for('subscriptions_rest', mailbox_slug=slug)

        response = c.get(subs_url)
        all_subs = json.loads(response.body)
        assert len(all_subs) == 0

        info = {'type': 'feed', 'title': title, 'url': url}
        response = c.post(subs_url, json.dumps(info), content_type='application/json', status=201)
        sub_slug = json.loads(response.body)['slug']
        info_url = self.url_for('subscription_rest', mailbox_slug=slug, 
                                sub_slug=sub_slug)

        c.head(info_url)

    def test_update_sub_post(self):
        """
        test updating a subscription by POST'ing to its url
        """
        
        url = 'http://example.com/feed/1'
        title = 'The Example Feed'

        url2 = 'http://example.com/feed/2'
        title2 = 'The Example Feed 2'

        mb = self.create_test_mailbox()
        slug =  get_mailbox_slug(self.config, mb.name)

        c = self.get_test_app()
        self.login_as_admin(c)

        subs_url = self.url_for('subscriptions_rest', mailbox_slug=slug)

        response = c.get(subs_url)
        all_subs = json.loads(response.body)

        assert len(all_subs) == 0

        info = {'type': 'feed', 'title': title, 'url': url}
        response = c.post(subs_url, json.dumps(info), content_type='application/json', status=201)
        sub_slug = json.loads(response.body)['slug']

        sub_url = self.url_for('subscription_rest', mailbox_slug=slug, 
                               sub_slug=sub_slug)

        response = c.get(sub_url)
        sub_info = json.loads(response.body)
        assert sub_info['type'] == 'feed'
        assert sub_info['title'] == title
        assert sub_info['url'] == url

        # POST some bad info, should fail and leave the sub unchanged
        info = {'title': title2, 'url': url2, 'some_bad-key': 'val'}
        c.post(sub_url, json.dumps(info), content_type='application/json', status=400)
        response = c.get(sub_url)
        sub_info = json.loads(response.body)
        assert sub_info['type'] == 'feed'
        assert sub_info['title'] == title
        assert sub_info['url'] == url

        # POST to change title and URL, valid, should change the sub
        info = {'title': title2, 'url': url2}
        c.post(sub_url, json.dumps(info), content_type='application/json')
        response = c.get(sub_url)
        sub_info = json.loads(response.body)
        assert sub_info['type'] == 'feed'
        assert sub_info['title'] == title2
        assert sub_info['url'] == url2

class TestUserAPI(RadarTestCase):
    
    def test_create_user_urlenc_post(self):
        """
        tests creating a user by POST'ing form-encoded parameters
        to /user
        """
        uname = 'joe'
        uid = 'org.couchdb.user:%s' % uname
        udb = self.get_users_database()

        create_url = self.url_for('create_user')

        assert not uid in udb
        c = self.get_test_app()
        self.login_as_admin(c)
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
        udb = self.get_users_database()

        create_url = self.url_for('create_user')

        assert not uid in udb
        c = self.get_test_app()
        self.login_as_admin(c)
        c.post(create_url, json.dumps({'username': uname}), content_type="application/json", status=201)
        assert uid in udb
        c.post(create_url, json.dumps({'username': uname}), content_type="application/json", status=409)
        del udb[uid]

        # test passwords.
        password = 'bl0w'
        bad_pass = 'b0w1'
        # missing password 2
        c.post(create_url, json.dumps({'username': uname, 'password': password}), 
               content_type="application/json", status=400)
        assert uid not in udb

        # passwords don't match
        c.post(create_url, json.dumps({'username': uname, 
                            'password': password, 
                            'password2': bad_pass}), 
                            content_type="application/json", status=400)
        assert uid not in udb

        # okay 
        c.post(create_url, json.dumps({'username': uname, 
                            'password': password, 
                            'password2': password}), 
                            content_type="application/json", status=201)
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
        udb = self.get_users_database()

        create_url = self.url_for('user_rest', userid=uname)

        assert not uid in udb
        c = self.get_test_app()
        self.login_as_admin(c)
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
        udb = self.get_users_database()

        create_url = self.url_for('user_rest', userid=uname)

        assert not uid in udb
        c = self.get_test_app()
        self.login_as_admin(c)
        c.put(create_url, json.dumps({}), 
              content_type="application/json", status=201)
        assert uid in udb
        c.put(create_url, json.dumps({}),
              content_type="application/json", status=409)
        del udb[uid]

        # test passwords.
        password = 'bl0w'
        bad_pass = 'b0w1'
        # missing password 2
        c.put(create_url, json.dumps({'password': password}), 
              content_type="application/json",
              status=400)
        assert uid not in udb

        # passwords don't match
        c.put(create_url, json.dumps({'password': password, 
                            'password2': bad_pass}), 
                            content_type="application/json",
                            status=400)
        assert uid not in udb

        # okay 
        c.put(create_url, json.dumps({'password': password, 
                           'password2': password}), 
                           content_type="application/json",
                           status=201)

        user = User.get_by_username(udb, uname)
        assert user.check_password(password)
        assert not user.check_password(bad_pass)

    
    def test_user_exists(self):
        uname = 'joe'
        udb = self.get_users_database()
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
        
        udb = self.get_users_database()
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

        udb = self.get_users_database()
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
               content_type="application/json", status=401)
        res = c.get(self.url_for('current_user_info'))
        info = json.loads(res.body)
        assert info['is_anonymous'] == True
        assert info.get('userid', None) is None

        # successfull login
        c.post(login_url, json.dumps({'username': uname, 'password': password}), 
               content_type="application/json", status=200)
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

    def test_login_basic_auth(self):
        uname = 'joe'
        password = 'bl0w'
        badpw = 'lb0w'

        udb = self.get_users_database()
        user = User(username=uname, password=password)
        user.store(udb)

        c = self.get_test_app()

        # not logged in 
        # res = c.get(self.url_for('current_user_info'))
        # info = json.loads(res.body)
        # assert info['is_anonymous'] == True
        # assert info.get('userid', None) is None
        

        bad_method = ('Authorization', 'Bad Bad=News')
        c.get(self.url_for('current_user_info'), headers=[bad_method], status=401)
        
        bad_auth = _basic_auth(uname, badpw)
        c.get(self.url_for('current_user_info'), headers=[bad_auth], status=401)
        
        # should be joe for this request
        good_auth = _basic_auth(uname, password)
        res = c.get(self.url_for('current_user_info'), headers=[good_auth])
        info = json.loads(res.body)
        assert info['is_anonymous'] == False
        assert info['userid'] == 'joe'

        # but this is not persistent
        res = c.get(self.url_for('current_user_info'))
        info = json.loads(res.body)
        assert info['is_anonymous'] == True
        assert info.get('userid', None) is None

    def test_basic_auth_overrides_cookie(self):
        uname = 'joe'
        password = 'bl0w'
        badpw = 'lb0w'
        
        uname2 = 'jane'
        password2 = 'j03'

        udb = self.get_users_database()
        user = User(username=uname, password=password)
        user.store(udb)

        user2 = User(username=uname2, password=password2)
        user2.store(udb)

        c = self.get_test_app()

        # not logged in 
        res = c.get(self.url_for('current_user_info'))
        info = json.loads(res.body)
        assert info['is_anonymous'] == True
        assert info.get('userid', None) is None

        # successfull login 
        login_url = self.url_for('login')
        c.post(login_url, {'username': user.username, 'password': password}, status=200)
        res = c.get(self.url_for('current_user_info'))
        info = json.loads(res.body)
        assert info['is_anonymous'] == False
        assert info['userid'] == user.username
        
        # do a request with basic auth for the other user...
        res = c.get(self.url_for('current_user_info'), headers=[_basic_auth(user2.username, password2)])
        info = json.loads(res.body)
        assert info['is_anonymous'] == False
        assert info['userid'] == user2.username
        
        # this should not affect the session.
        res = c.get(self.url_for('current_user_info'))
        info = json.loads(res.body)
        assert info['is_anonymous'] == False
        assert info['userid'] == user.username

    def test_delete_user(self):
        uname = 'joe'
        udb = self.get_users_database()
        user_url = self.url_for('user_rest', userid=uname)
        user = User(username=uname)
        user.store(udb)

        c = self.get_test_app()
        self.login_as_admin(c)
        c.head(user_url, status=200)
        c.delete(user_url, status=200)
        c.head(user_url, status=404)
        c.delete(user_url, status=404)

    def test_update_user_passwd_post_json(self):
        uname = 'joe'
        pw1 = 'bl0w'
        pw2 = 'b0w1'
        udb = self.get_users_database()
        user_url = self.url_for('user_rest', userid=uname)
        c = self.get_test_app()
        self.login_as_admin(c)
        c.post(user_url, '', status=404)
    
        user = User(username=uname, password=pw1)
        user.store(udb)
        
        user = User.get_by_username(udb, uname)
        assert user.check_password(pw1)
        assert not user.check_password(pw2)

        # missing password2
        c.post(user_url, json.dumps({'username': uname, 'password': pw2}), 
               content_type="application/json", status=400)
        user = User.get_by_username(udb, uname)
        assert user.check_password(pw1)
        assert not user.check_password(pw2)

        # passwords don't match
        c.post(user_url, json.dumps({'username': uname, 
                            'password': pw2, 
                            'password2': pw1}), 
                            content_type="application/json", status=400)
        user = User.get_by_username(udb, uname)
        assert user.check_password(pw1)
        assert not user.check_password(pw2)


        # okay 
        c.post(user_url, json.dumps({'username': uname, 
                            'password': pw2, 
                            'password2': pw2}), 
                            content_type="application/json", status=200)
        user = User.get_by_username(udb, uname)
        assert user.check_password(pw2)
        assert not user.check_password(pw1)


    def test_update_user_passwd_post_urlenc(self):
        uname = 'joe'
        pw1 = 'bl0w'
        pw2 = 'b0w1'
        udb = self.get_users_database()
        user_url = self.url_for('user_rest', userid=uname)
        c = self.get_test_app()
        self.login_as_admin(c)
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


class TestMessageREST(RadarTestCase):
    
    def test_message_delete(self):
        """
        test deleting a message by DELETE
        """
        from radarpost.mailbox import *
        
        message1 = Message(title='Message 1')
        message2 = Message(title='Message 2')
        
        mb = self.create_test_mailbox()
        slug =  get_mailbox_slug(self.config, mb.name)

        c = self.get_test_app()
        self.login_as_admin(c)

        message1.store(mb)
        message2.store(mb)

        assert message1.id in mb
        assert message2.id in mb
        
        c.delete(self.url_for('message_rest', mailbox_slug=slug, message_slug=message1.id))
        
        assert message1.id not in mb
        assert message2.id in mb
        


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
            self.login_as_admin(c)
            
            c.head(mb_url, status=404)
            c.put(mb_url, '{}', content_type="application/json", status=201)
            c.head(mb_url, status=200)

            
            mb = get_mailbox(self.config, slug)
            assert mb is not None
            assert is_mailbox(mb)
        finally:
            dbname = get_database_name(self.config, slug)
            couchdb = get_couchdb_server(self.config)
            if dbname in couchdb: 
                del couchdb[dbname]
    
    def test_mailbox_update(self):
        mb = self.create_test_mailbox()
        slug = get_mailbox_slug(self.config, mb.name)
        mb_url = self.url_for('mailbox_rest', mailbox_slug=slug)
        c = self.get_test_app()
        self.login_as_admin(c)
        
        new_title = "The Test Mailbox's New Title"
        mbinfo = MailboxInfo.get(mb)
        assert mbinfo.title != new_title
        
        c.post(mb_url, json.dumps({'title': new_title}), 
               content_type="application/json", status=200)

        mbinfo = MailboxInfo.get(mb)
        assert mbinfo.title == new_title
        
        
    def test_mailbox_delete(self):
        """
        test deleting a mailbox
        """
        mb = self.create_test_mailbox()
        slug = get_mailbox_slug(self.config, mb.name)
        mb_url = self.url_for('mailbox_rest', mailbox_slug=slug)
        c = self.get_test_app()
        self.login_as_admin(c)
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
        opml_url = self.url_for('subscriptions_opml', mailbox_slug=slug)
        response = c.get(opml_url, status=200)
        feeds = feeds_in_opml(response.body)
        
        assert len(feeds.keys()) == 0

    def test_post_bad_opml(self):
        mb = self.create_test_mailbox()
        slug = get_mailbox_slug(self.config, mb.name)
        c = self.get_test_app()
        opml_url = self.url_for('subscriptions_opml', mailbox_slug=slug)
        opml = "this ain't opml"
        c.post(opml_url, opml, content_type='text/xml', status=400)

    def test_put_bad_opml(self):
        mb = self.create_test_mailbox()
        slug = get_mailbox_slug(self.config, mb.name)
        c = self.get_test_app()
        opml_url = self.url_for('subscriptions_opml', mailbox_slug=slug)
        opml = "this ain't opml"
        c.put(opml_url, opml, content_type='text/xml', status=400)


    def test_opml_post(self):
        mb = self.create_test_mailbox()
        slug = get_mailbox_slug(self.config, mb.name)
        c = self.get_test_app()
        
        opml_url = self.url_for('subscriptions_opml', mailbox_slug=slug)
    
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
        
        opml_url = self.url_for('subscriptions_opml', mailbox_slug=slug)
    
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
        
        opml_url = self.url_for('subscriptions_opml', mailbox_slug=slug)
    
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

        opml_url = self.url_for('subscriptions_opml', mailbox_slug=slug)

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

def _basic_auth(un, passwd):
    auth = "Basic %s" % base64.b64encode('%s:%s' % (un, passwd))
    return ('Authorization', auth)

