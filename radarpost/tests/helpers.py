import os
from os import path
from os.path import dirname as dn
import copy
from couchdb import Server
from couchdb.http import PreconditionFailed
from datetime import datetime, timedelta
from hashlib import sha1
import random
import struct

from radarpost.mailbox import create_mailbox as _create_mailbox
from radarpost.config import load_config

TEST_INI_KEY = 'RADAR_TEST_CONFIG'
DEFAULT_RADAR_TEST_CONFIG = path.join(dn(dn(dn(__file__))), 'test.ini')
TEST_DATA_DIR = path.join(dn(__file__), 'data')
TEST_MAILBOX_ID = 'rp_test_mailbox'

def get_config_filename():
    filename = os.environ.get('RADAR_TEST_CONFIG', None)
    if filename is None:
        filename = DEFAULT_RADAR_TEST_CONFIG
    return filename

def load_test_config():
    return load_config(get_config_filename())

def get_data(filename):
    return open(path.join(TEST_DATA_DIR, filename)).read()

def create_test_mailbox(config=None, name=TEST_MAILBOX_ID):
    if config is None: 
        config = load_test_config()
    try:
        couchdb = Server(config['couchdb.address'])
        return _create_mailbox(couchdb, name)
    except PreconditionFailed:        
        del couchdb[name]
        return _create_mailbox(couchdb, name)

def create_test_users_db(config=None):
    if config is None: 
        config = load_test_config()
    name = config['couchdb.users_database']
    try:
        couchdb = Server(config['couchdb.address'])
        return couchdb.create(name)
    except PreconditionFailed:        
        del couchdb[name]
        return couchdb.create(name)

def rfc3339(value):
    if value is None:
        return ''

    if value.tzinfo:
        off = value.tzinfo.utcoffset(value)
        mins = (off.days * 24 * 60) + (offset.seconds / 60)
        tz = "%+02d:%02d" % (mins / 60, mins % 60)
    else:
        # zulu time
        tz = 'Z'

    return value.strftime('%Y-%m-%dT%H:%M:%S') + tz


def create_atom_feed(feed_info, items): 
    """
    create a dummy atom feed. 
    
    feed_info: dict
       - id 
       - timestamp

    items: list of dict 
       - id 
       - title
       - author
       - content
       - timestamp
    """
    
    entries = ""
    for e in items: 
        ee = copy.deepcopy(e)
        ee['timestamp'] = rfc3339(ee['timestamp'])
        entries += ATOM_ENTRY_TEMPLATE % ee
    
    ff = copy.deepcopy(feed_info)
    ff['timestamp'] = rfc3339(ff['timestamp'])
    ff['entries'] = entries
    
    return ATOM_FEED_TEMPLATE % ff
    
def random_id():
    hasher = sha1()
    hasher.update("".join(chr(random.randrange(0, 256)) for i in xrange(64)))
    return hasher.hexdigest()



def random_feed_info(info=None):
    """
    create a random feed info structure.  If a dict is 
    given, the random info is updated with items from 
    the dict.
    """ 
    feed_id = random_id()
    ff = {}
    ff['id'] = ff['url'] = 'http://example.com/feeds/%s' % feed_id
    ff['title'] = 'Feed %s' % feed_id
    ff['timestamp'] = datetime.utcnow()
    
    if info is not None:
        ff.update(info)
    return ff

def random_feed_entry(info=None):
    entry_id = random_id()
    fe = {}
    fe['id'] = 'http://example.com/items/%s' % entry_id
    fe['title'] = 'Entry %s' % entry_id
    fe['timestamp'] = datetime.utcnow()
    fe['author'] = 'A. Nonymous'
    fe['link'] = 'http://example.com/items/%s/view' % entry_id
    fe['content'] = "<p>This is the body of the item '%s'.</p>" % entry_id
    
    if info is not None:
        fe.update(info)
    return fe
        
def random_feed_entries(nitems, timestamp=None):
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    entries = []
    for i in range(nitems):
        entries.append(random_feed_entry(info={'timestamp': timestamp}))
        timestamp = timestamp - timedelta(seconds=1)
    
    return entries
    
def random_feed_info_and_entries(nitems=10):
    info = random_feed_info()
    entries = random_feed_entries(nitems, timestamp=info['timestamp'])
    return info, entries
    
    

ATOM_FEED_TEMPLATE = \
"""
<?xml version="1.0" encoding="utf-8" ?>

<feed xmlns="http://www.w3.org/2005/Atom">
  
  <id>%(id)s</id>
  
  <link rel="self" href="%(url)s" />

  <title type="html">
    <![CDATA[%(title)s]]>
  </title>

  <updated>%(timestamp)s</updated>
   
  %(entries)s
</feed>
"""

ATOM_ENTRY_TEMPLATE = \
"""
<entry>
  <id>%(id)s</id>
  
  <title type="html">
    <![CDATA[%(title)s]]>
  </title>

  <updated>%(timestamp)s</updated>

  <author>
    <name>%(author)s</name>
  </author>

  <link rel="alternate" href="%(link)s" />
  
  <content type="html">
    <![CDATA[%(content)s]]>
  </content>

</entry>
"""
