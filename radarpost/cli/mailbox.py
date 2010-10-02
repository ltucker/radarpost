from couchdb import Server, ResourceConflict, ResourceNotFound
from datetime import datetime
import logging
import traceback
from radarpost.feed import *
from radarpost.mailbox import *
from radarpost.main import COMMANDLINE_PLUGIN, BasicCommand, get_basic_option_parser
from radarpost.main import find_command, print_basic_usage, print_unknown_command
from radarpost import plugins

log = logging.getLogger(__name__)

class MailboxesCommand(BasicCommand):

    def setup_options(self, parser):
        parser.set_usage(r"%prog " + "%s [mailbox] [mailbox] ... [options]" % self.command_name)
        parser.add_option('--all', action='store_true', dest="update_all", default=False, help="update all mailboxes")
        
    def __call__(self, config, options, args):
        if options.update_all and len(args) != 1:
            print "Cannot specify --all and list of mailboxes."
            self.print_usage()
            return 1

        couchdb = Server(config['couchdb.address'])
        prefix = config['couchdb.prefix']

        if options.update_all:
            self._do_update(iter_mailboxes(couchdb, prefix=prefix), 
                            config, options)
        else:
            selected = []
            for slug in args[1:]:
                name = prefix + slug
                if not name in couchdb: 
                    print 'Mailbox "%s" does not exist' % slug
                    return 1
                selected.append(couchdb[name])
            self._do_update(selected, config, options)

class UpdateSubscriptionsCommand(MailboxesCommand):

    command_name = 'update'
    description = 'update subscriptions in a mailbox'

    def _do_update(self, mailboxes, config, options):
        for mb in mailboxes:
            for sub in Subscription.view(mb, Subscription.by_type, include_docs=True):
                try:
                    self._update_subscription(mb, sub, config, options)
                except: 
                    log.error('%s: error updating subscription "%s" of type "%s": %s' % 
                        (mb.name, sub.id, sub.subscription_type, traceback.format_exc()))
    def _update_subscription(self, mailbox, sub, config, options):
        for handler in plugins.get(SUBSCRIPTION_UPDATE_HANDLER):
            if handler(mailbox, sub, config) == True:
                return True
        log.info('%s: no update handler for subscription "%s" of type "%s"' % 
                 (mb.name, sub.id, sub.subscription_type))
        return False

plugins.register(UpdateSubscriptionsCommand(), COMMANDLINE_PLUGIN)