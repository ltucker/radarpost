from couchdb import Server, PreconditionFailed
import json
from routes.util import URLGenerator
from unittest import TestCase
from radarpost.mailbox import create_mailbox as _create_mailbox
from radarpost.user import User, ROLE_ADMIN
from radarpost.tests.helpers import load_test_config
from radarpost.web.context import build_routes
from radarpost.web.context import get_couchdb_server, get_database_name
from radarpost.web.context import get_mailbox

__all__ = ['RadarTestCase']

class RadarTestCase(TestCase):
    """
    helpful base class for testing web interfaces 
    of radarpost
    """
    
    TEST_MAILBOX_SLUG = '__rp_test_mailbox'

    def setUp(self):
        self.config = load_test_config()
        self.url_gen = URLGenerator(build_routes(self.config), {})

        # set-up users database
        couchdb = get_couchdb_server(self.config)
        dbname = self.config['couchdb.users_database']
        if dbname in couchdb: 
            del couchdb[dbname]
        self._users_db = couchdb.create(dbname)
        
        # create an admin
        admin = User(username=self.config['test.admin_user'],
                     password=self.config['test.admin_password'])
        admin.roles = [ROLE_ADMIN]
        admin.store(self._users_db)

    def login_as_admin(self, app):
        return self.login_as(self.config['test.admin_user'],
                             self.config['test.admin_password'], app)

    def login_as(self, username, password, app):
        login_url = self.url_for('login')
        return app.post(self.url_for('login'), {'username': username, 'password': password}, status=200)

    def logout(self, app):
        app.post(self.url_for('logout'), {}, status=200)

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
        self.login_as_admin(c)
        mb_url = self.url_for('mailbox_rest', mailbox_slug=slug)
        response = c.head(mb_url, status='*')
        if response.status_int != 404:
            response = c.delete(mb_url, status=200)
        c.put(mb_url, '{}', content_type="application/json", status=201)
        self.logout(c)
        return get_mailbox(self.config, slug)

    def get_users_database(self):
        return self._users_db