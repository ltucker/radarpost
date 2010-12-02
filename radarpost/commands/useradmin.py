from couchdb import Server, ResourceNotFound
from radarpost.cli import COMMANDLINE_PLUGIN, BasicCommand, get_basic_option_parser
from radarpost import plugins
from radarpost.user import User, ROLE_ADMIN
from getpass import getpass

class CreateUserCommand(BasicCommand):

    command_name = 'create_user'
    description = 'create a user'

    @classmethod
    def setup_options(cls, parser):
        parser.set_usage(r"%prog" + "%s <username> [options]" % cls.command_name)
        parser.add_option('--admin', action="store_true", dest="is_admin",
                          default=False, help="create an administrative user")
        parser.add_option('--locked', action="store_true", dest="is_locked",
                          default=False, 
                          help="create with locked password, do not prompt for password.")


    def __call__(self, username, is_locked=False, is_admin=False):
        """
        Create a user with the given username. 
        is_locked - if True, create with a locked password
        is_admin  - if True, grant administrative rights to the user
        """
        couchdb = Server(self.config['couchdb.address'])
        try:
            udb = couchdb[self.config['couchdb.users_database']]
        except: 
            print "Failed to connect to couchdb at %s/%s" % (self.config['couchdb.address'], 
                                                             self.config['couchdb.users_database'])
            return 1
            
        new_user = User(username=username)
        if new_user.id in udb: 
            print 'User "%s" already exists' % username
            return 1
        
        if not is_locked:
            done = False
            while(not done):
                password = getpass(prompt="Password for %s: " % username)
                password2 = getpass(prompt="Repeat password: ")
                if password == password2: 
                    done = True
                else: 
                    print "Passwords did not match, try again.\n"        
            new_user.set_password(password)

        if is_admin:
            new_user.roles = [ROLE_ADMIN]

        new_user.store(udb)
        print 'Created user "%s"' % username
plugins.register(CreateUserCommand, COMMANDLINE_PLUGIN)




class ResetPasswordCommand(BasicCommand):

    command_name = 'reset_password'
    description = "reset a user's password"

    @classmethod
    def setup_options(cls, parser):
        parser.set_usage(r"%prog" + "%s <username> [options]" % cls.command_name)
        parser.add_option('--locked', action="store_true", dest="is_locked",
                          default=False, 
                          help="lock the user's password, do not prompt for password.")


    def __call__(self, username, is_locked=False):
        """
        Reset the password of the user with the given username.
        is_locked - if True, lock the user's password
        """
        couchdb = Server(self.config['couchdb.address'])
        try:
            udb = couchdb[self.config['couchdb.users_database']]
        except: 
            print "Failed to connect to couchdb at %s/%s" % (self.config['couchdb.address'], 
                                                             self.config['couchdb.users_database'])
            return 1
        
        try:
            user = User.get_by_username(udb, username)
        except ResourceNotFound: 
            print 'User "%s" does not exist' % username
            return 1
            
        if not is_locked:
            done = False
            while(not done):
                password = getpass(prompt="New password for %s: " % username)
                password2 = getpass(prompt="Repeat password: ")
                if password == password2: 
                    done = True
                else: 
                    print "Passwords did not match, try again.\n"        
            user.set_password(password)
        else: 
            user.lock_password()

        user.store(udb)
        print 'Password changed for user "%s"' % username
plugins.register(ResetPasswordCommand, COMMANDLINE_PLUGIN)