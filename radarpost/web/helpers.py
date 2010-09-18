from couchdb import Server, ResourceNotFound
from django.conf import settings
from radarpost.mailbox import iter_mailboxes as _iter_mailboxes

__all__ = ['get_couchdb_server', 'get_database_name', 'get_mailbox_slug', 
           'get_mailbox', 'get_mailbox_db_prefix']

def get_couchdb_server():
    """
    get a connection to the configured couchdb server. 
    """
    if hasattr(settings, 'COUCHDB'):
        return Server(settings.COUCHDB)
    else:
        return Server()

def get_database_name(mailbox_slug):
    """
    get the database name corresponding to the 
    given mailbox slug.
    """
    return '%s%s' % (get_mailbox_db_prefix(), mailbox_slug)

def get_mailbox_slug(dbname):
    """
    get the slug for the mailbox with the 
    database name specified.
    """
    prefix = get_mailbox_db_prefix()
    if dbname.startswith(prefix):
        return dbname[len(prefix):]
    else:
        return dbname

def get_mailbox(mailbox_slug, couchdb=None):
    """
    get a connection to the couchdb database with the 
    given slug. 
    """

    if couchdb is None:
        couchdb = get_couchdb_server()
    try:
        return couchdb[get_database_name(mailbox_slug)]
    except ResourceNotFound:
        return None

def get_mailbox_db_prefix():
    """
    gets the configured name prefix for all couchdb databases 
    representing mailboxes.
    """
    if hasattr(settings, 'COUCHDB_PREFIX'):
        prefix = settings.COUCHDB_PREFIX
    else:
        prefix = 'radar/'
    return prefix
    
def iter_mailboxes(couchdb=None):
    if couchdb is None:
        couchdb = get_couchdb_server()
    return _iter_mailboxes(couchdb, prefix=get_mailbox_db_prefix())