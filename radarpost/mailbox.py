import copy
from couchdb.mapping import *
from couchdb.http import ResourceNotFound, PreconditionFailed
from datetime import datetime
import logging
from radarpost import plugins

__all__ = ['Message', 'SourceInfo', 'Subscription', 'MailboxInfo', 
           'MESSAGE_TYPE', 'SUBSCRIPTION_TYPE', 'MAILBOXINFO_TYPE', 
           'MAILBOXINFO_ID', 'DESIGN_DOC', 'DESIGN_DOC_PLUGIN', 
           'create_mailbox', 'is_mailbox', 'bless_mailbox', 'iter_mailboxes',
           'trim_mailbox', 'refresh_views', 'get_json_raw_url']

log = logging.getLogger(__name__)

####################################################
#
# Plug-in slots
#
####################################################
DESIGN_DOC_PLUGIN = 'mailbox.design_doc'
"""
This plugin slot accepts a dictionary representing a design document.

Objects in the slot are added as design documents to all mailboxes 
that are created.
"""

class RadarDocument(Document):
    """
    Helper class to define methods available to all documents.
    """
    
    def user_update(self, params):
        for k, v in params.items():
            if not hasattr(self, k): 
                raise AttributeError('Object %s has no attribute %s' % (self, k))
            if hasattr(self, 'user_updatable') and not k in self.user_updatable:
                raise AttributeError('Cannot update attribute %s on %s' % (k, self))
            
            setattr(self, k, v)

class DowncastDoc(RadarDocument):
    """
    When a DowncastDoc is returned from a view on a base class, 
    it's instance type is determined by plugins. the intent is
    to allow subclass instances with different behaviors and 
    fields to be returned from a view.  eg a FeedSubscription 
    when getting all Subscriptions.
    """

    @classmethod
    def create_type(cls, typename):
        instance = None
        if typename: 
            for create in plugins.get(cls.SUBTYPE_PLUGIN):
                instance = create(typename) 
                if instance is not None:
                    break
        if instance is None:
            instance = cls()
        return instance

    @classmethod
    def wrap(cls, data):
        instance = cls.create_type(data.get(cls.SUBTYPE_FIELD))
        instance._data = data
        return instance

#####################################################
#
# Basic Document Types
#
#####################################################

MESSAGE_TYPE = 'message'
SUBSCRIPTION_TYPE = 'subscription'
MAILBOXINFO_TYPE = 'mailboxinfo'
MAILBOXINFO_ID = 'mailbox_meta'


class SourceInfo(Mapping):
    """
    denormalized information about the source of a given 
    message that is kept inside a message.
    """
    subscription_id = TextField()
    subscription_type = TextField()
    title = TextField()

class Message(DowncastDoc):
    """
    A message in a mailbox.
    """
    
    type = TextField(default=MESSAGE_TYPE)
    message_type = TextField()
    fingerprint = TextField()
    timestamp = DateTimeField()
    source = DictField(SourceInfo)

    # helpful view constants
    by_timestamp = '_design/mailbox/_view/messages_by_timestamp'

    SUBTYPE_PLUGIN = 'radar.mailbox.mailbox_subtype'
    SUBTYPE_FIELD = 'message_type'

class Subscription(DowncastDoc):
    """
    Represents a subscription to a particular
    source of messages by a mailbox.
    """
    type = TextField(default=SUBSCRIPTION_TYPE)
    subscription_type = TextField()
    title = TextField()
    status = TextField()
    last_update = DateTimeField()

    # helpful view constants
    by_type = '_design/mailbox/_view/subscriptions_by_type'

    # status constants
    STATUS_OK        = 'ok'
    STATUS_ERROR     = 'error'
    STATUS_UNCHANGED = 'unchanged'
    
    SUBTYPE_PLUGIN = 'radar.mailbox.subscription_subtype'
    SUBTYPE_FIELD = 'subscription_type'

    user_updatable = ('title', )

class MailboxInfo(RadarDocument):
    """
    General metadata about a mailbox.
    """
    type = TextField(default=MAILBOXINFO_TYPE)
    version = TextField(default="0.0.1")
    title = TextField()
    
    def __init__(self, **values):
        Document.__init__(self, id=MAILBOXINFO_ID, **values)
    
    @classmethod
    def get(cls, mailbox):
        return MailboxInfo.load(mailbox, MAILBOXINFO_ID)

    user_updatable = ('title', )

#####################################################
#
# Helpers for creating and managing mailbox databases
#
#####################################################

def create_mailbox(couchdb, dbname):
    """
    create a mailbox on the given server with the given name.
    
    raises PreconditionFailed if a database with the given name 
           already exists.
    raises ValueError if name is not a valid mailbox name.
    """
    db = couchdb.create(dbname)
    bless_mailbox(db)
    return db

def iter_mailboxes(couchdb, prefix=None): 
    """
    iterate through mailboxes in the current context.
    if prefix is specified, only databases with names
    that start with the string specified are returned.
    """
    for db_name in couchdb:
        db = couchdb[db_name]
        if prefix is not None and not db_name.startswith(prefix):
            continue
        if is_mailbox(db):
            yield db
 
def bless_mailbox(db):
    """
    bootstrap a database as a Mailbox
    """
    info = MailboxInfo()
    info.store(db)
    update_mailbox(db)

def update_mailbox(db):
    """
    update database design document and other
    metadata.  This operation unconditionally
    clobbers the current design document in the 
    database.
    """
    if not is_mailbox(db):
        raise PreconditionFailed("database %s is not a mailbox" % db.name)

    for dd in plugins.get(DESIGN_DOC_PLUGIN):
        dd = copy.deepcopy(dd)
        cur = db.get(dd['_id'])
        if cur:
            dd['_rev'] = cur['_rev']
        db[dd['_id']] = dd


def is_mailbox(db):
    try:
        # check for the existance of the 
        # mailboxinfo document.
        info = db[MAILBOXINFO_ID]
        # check that the type field of the info doc 
        # matches the expected type.
        if info.get('type', None) != MAILBOXINFO_TYPE:
            return False
        # could do other validation here...
        return True
    except ResourceNotFound:
        # if it's not there, not a mailbox
        return False

def get_json_raw_url(mb, path):
    """
    little workaround for skirting overzealous 
    couchdb-python quoting behavior. 
    """
    from couchdb import http, json
    session = mb.resource.session
    creds = mb.resource.credentials
    method = 'GET'
    path = [mb.resource.url] + path
    url = http.urljoin(*path)
    status, headers, data = session.request(method, url, credentials=creds)
    if 'application/json' in headers.get('content-type'):
        data = json.decode(data.read())
    return status, headers, data
    
#####################################################
#
# Helpful operations over mailboxes
#
#####################################################

def trim_mailbox(mb, max_age, batch_size=100):
    max_date = datetime.utcnow() - max_age


    params = {}
    params['startkey'] = DateTimeField()._to_json(max_date)
    params['reduce'] = False
    params['descending'] = True
    params['limit'] = batch_size

    errors = 0
    deletes = 0
    done = False
    
    while not done: 
        updates = []
        for mrow in mb.view(Message.by_timestamp, **params):
            updates.append({'_id': mrow.id, 
                            '_rev': mrow.value['_rev'],
                            '_deleted': True})
    
        if len(updates) == 0:
            break
        if len(updates) < batch_size:
            done = True
    
        for (success, did, rev_exc) in mb.update(updates): 
            if success:
                deletes += 1
            else:
                errors += 1
        refresh_views(mb)

    return deletes

def refresh_views(mb):
    for dd in plugins.get(DESIGN_DOC_PLUGIN):
        if 'views' in dd and len(dd['views'].keys()) > 0:
            first_view = dd['views'].keys()[0]
            view_url = '%s/%s' % (dd['_id'], first_view)
            log.info("Refreshing views in %s..." % dd['_id'])
            try:
                mb.view(view_url, {'count': 0})
                # aaaand wait...
            except: 
                log.error("failed to refresh view %s: %s" % 
                          (view_url, traceback.format_exc()))

#####################################################
#
# Main mailbox design document 
#
#####################################################


DESIGN_DOC = {
    '_id': '_design/mailbox',
    'views': {
        'messages_by_timestamp': {
            'map':
                """
                function(doc) {
                    if (doc.type == 'message') {
                        emit(doc.timestamp, {'_rev': doc._rev});
                    }
                }
                """,
            'reduce':
                """
                function(key, values, rereduce) {
                    if (rereduce == true) {
                        return sum(values);
                    }
                    else {
                        return values.length;
                    }
                }
                """
        },

        'subscriptions_by_type': {
            'map': 
                """
                function(doc) {
                    if (doc.type == 'subscription') {
                        emit(doc.subscription_type, {'_rev': doc._rev});
                    }
                }
                """
        }
    },
    'filters': {
    }
}
plugins.register(DESIGN_DOC, DESIGN_DOC_PLUGIN)