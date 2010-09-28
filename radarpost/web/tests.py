from couchdb import Server, PreconditionFailed
import json
from routes.util import URLGenerator
from unittest import TestCase
from radarpost.mailbox import create_mailbox as _create_mailbox
from radarpost.web.context import build_routes
from radarpost.web.context import get_couchdb_server, get_database_name
from radarpost.web.context import get_mailbox

__all__ = ['RadarTestCase']

class RadarTestCase(TestCase):

    TEST_MAILBOX_SLUG = '__rp_test_mailbox'
    TEST_USERS_DB = 'rp_test_users'

    def setUp(self):
        # XXX load it!
        self.config = {'apps': ['radarpost.web.api'], 
                       'debug': True, 
                       'session.type': 'memory', 
                       'users_database': self.TEST_USERS_DB}

        self.url_gen = URLGenerator(build_routes(self.config), {})

    def tearDown(self):
        couchdb = get_couchdb_server(self.config)
        dbname = get_database_name(self.config, self.TEST_MAILBOX_SLUG)
        if dbname in couchdb:
            del couchdb[dbname]
        
    def url_for(self, *args, **kw):
        return self.url_gen(*args, **kw)
        
    def get_test_app(self):
        from radarpost.web.app import make_app
        from webtest import TestApp
        return TestApp(make_app(self.config))

    def create_test_mailbox(self, slug=None):
        if slug is None:
            slug = self.TEST_MAILBOX_SLUG
        c = self.get_test_app()
        mb_url = self.url_for('mailbox_rest', mailbox_slug=slug)
        response = c.head(mb_url, status='*')
        if response.status_int != 404:
            response = c.delete(mb_url, status=200)
        c.post(mb_url, '{}', content_type="application/json", status=201)
        return get_mailbox(self.config, slug)

    def create_users_database(self):
        couchdb = get_couchdb_server(self.config)
        dbname = self.config['users_database']
        if dbname in couchdb: 
            del couchdb[dbname]
        return couchdb.create(dbname)
