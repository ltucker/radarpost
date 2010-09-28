from couchdb.mapping import *
from couchdb.http import ResourceNotFound, PreconditionFailed
from hashlib import sha1
from random import choice
from string import digits

LOCKED_PASSWORD = "*locked*"
class User(Document):
    """
    This is a representation of a 'standard' couchdb user
    document.  Creating one of these in the couchdb users
    database (usually _users) adds a database user.  They 
    can be created elsewhere if database level access is 
    not desirable.
    
    See http://wiki.apache.org/couchdb/Security_Features_Overview
    
    """
    def __init__(self, username=None, password=None):
        """
        User may be initialized with the special keyword arguments
        username and password for creating a new User:
        
        u = User(username=joe, password="bl0w")
        """
        Document.__init__(self)

        if 'username' is not None: 
            self.id = 'org.couchdb.user:%s' % username
            self['name'] = username
    
        if password is not None:
            self.set_password(password)
        else: 
            self.lock_password()

    @classmethod
    def get_by_username(cls, db, username):
        natid = 'org.couchdb.user:%s' % username
        return cls.load(db, natid)

    @property
    def username(self):
        return self['name']

    def get_public_id(self):
        # same for now.
        return self.username

    type = TextField(default="user")
    roles = ListField(TextField)
    password_sha = TextField()
    salt = TextField()

    def set_password(self, plaintext_password):
        self.salt = _generate_salt()
        self.password_sha = _password_hash(plaintext_password, self.salt)

    def lock_password(self):
        self.password_sha = LOCKED_PASSWORD
        
    def check_password(self, plaintext_password):
        if self.password_sha == LOCKED_PASSWORD:
            return False
        hashed_pw = _password_hash(plaintext_password, self.salt)
        return self.password_sha == hashed_pw

    def is_anonymous(self):
        return False

def _password_hash(password, salt):
    hasher = sha1()
    hasher.update(password)
    hasher.update(salt)
    return hasher.hexdigest()

def _generate_salt():
    """
    generate a random 128 bit hexadecimal salt value
    """
    chars = "0123456789abcdef"
    salt = ''
    for i in range(32):
        salt +=  choice(chars)
    return salt

class AnonymousUser(object):
    def is_anonymous(self):
        return True