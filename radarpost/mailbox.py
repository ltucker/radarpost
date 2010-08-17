import copy
from couchdb.mapping import *
from couchdb.http import ResourceNotFound, PreconditionFailed

__all__ = ['Message', 'SourceInfo', 'Subscription', 'MailboxInfo', 
           'MESSAGE_TYPE', 'SUBSCRIPTION_TYPE', 'MAILBOXINFO_TYPE', 
           'MAILBOXINFO_ID', 'DESIGN_DOC', 'create_mailbox', 'get_mailbox', 
           'delete_mailbox', 'is_mailbox', 'bless_mailbox']


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


class Message(Document):
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

class Subscription(Document):
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

class MailboxInfo(Document):
    """
    General metadata about a mailbox.
    """
    type = TextField(default=MAILBOXINFO_TYPE)
    version = TextField(default="0.0.1")
    name = TextField()


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

def iter_mailboxes(couchdb): 
    """
    iterate through mailboxes in the current context.
    """
    for db_name in couchdb:
        db = couchdb[db_name]
        if is_mailbox(db):
            yield db
 
def bless_mailbox(db):
    """
    bootstrap a database as a Mailbox
    """
    info = MailboxInfo(id=MAILBOXINFO_ID)
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

    dd = copy.deepcopy(DESIGN_DOC)
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
                        emit(doc.timestamp, null);
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
                        emit(doc.subscription_type);
                    }
                }
                """
        }
    },
    'filters': {
    }
}
