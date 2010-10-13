from couchdb import Server, ResourceConflict, ResourceNotFound
from datetime import datetime, timedelta
import logging
import traceback
from radarpost.agent import SUBSCRIPTION_UPDATE_HANDLER
from radarpost.feed import *
from radarpost.mailbox import *
from radarpost.main import COMMANDLINE_PLUGIN, BasicCommand, get_basic_option_parser
from radarpost.main import find_command, print_basic_usage, print_unknown_command
from radarpost import plugins

log = logging.getLogger(__name__)

class MailboxHelper(object):

    def _get_mailbox(self, slug, config):
        couchdb = Server(config['couchdb.address'])
        prefix = config['couchdb.prefix']
        
        name = prefix + slug
        if not name in couchdb: 
            print 'Mailbox "%s" does not exist' % slug
            return None
        
        mb = couchdb[name]
        if not is_mailbox(mb): 
            print 'database %s is not a mailbox.' % name
            return None
        
        return mb

    def _update_subscription(self, mailbox, sub, config, options):
        for handler in plugins.get(SUBSCRIPTION_UPDATE_HANDLER):
            if handler(mailbox, sub, config) == True:
                return True
        log.info('%s: no update handler for subscription "%s" of type "%s"' % 
                 (mb.name, sub.id, sub.subscription_type))
        return False

class MailboxesCommand(BasicCommand, MailboxHelper):

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
                mb = self._get_mailbox(slug, config)
                if mb is None: 
                    return 1
                else: 
                    selected.append(mb)
            if len(selected) == 0: 
                self.print_usage()
                return
                
            self._do_update(selected, config, options)

class UpdateSubscriptionsCommand(MailboxesCommand):

    command_name = 'update'
    description = 'update all subscriptions in a set of mailboxes'

    def _do_update(self, mailboxes, config, options):
        for mb in mailboxes:
            for sub in Subscription.view(mb, Subscription.by_type, include_docs=True):
                try:
                    self._update_subscription(mb, sub, config, options)
                except: 
                    log.error('%s: error updating subscription "%s" of type "%s": %s' % 
                        (mb.name, sub.id, sub.subscription_type, traceback.format_exc()))

plugins.register(UpdateSubscriptionsCommand(), COMMANDLINE_PLUGIN)

class UpdateSubscriptionCommand(BasicCommand, MailboxHelper):

    command_name = 'update_sub'
    description = 'update a particular subscription in a mailbox'

    def setup_options(self, parser):
        parser.set_usage(r"%prog " + "%s mailbox [options]" % self.command_name)
        parser.add_option('--id', dest="sub_id", help="specify subscription by id")
        parser.add_option('--feed', dest="feed_url", help="specify subscription by feed url")

    def __call__(self, config, options, args):
        if len(args) != 2:
            self.print_usage()
            return 1

        mb = self._get_mailbox(args[1], config)
        if mb is None: 
            return 1
    
        if options.feed_url:
            params = {
                'include_docs': True,
                'startkey': options.feed_url,
                'endkey': options.feed_url
            }
            sub = None
            for sub in Subscription.view(mb, FeedSubscription.by_url, **params):
                break
    
            if sub is None: 
                print "No subscription with url %s in mailbox %s" % (options.feed_url, mb.name)
            else: 
                print "Found subscription for %s (%s)" % (options.feed_url, sub.id)
                self._update_subscription(mb, sub, config, options)
        elif options.sub_id:
            sub = Subscription.load(mb, options.sub_id)
            if sub is None or not sub.type == SUBSCRIPTION_TYPE: 
                print "No subscription with id %s found in mailbox %s" % (options.sub_id, mb.name)
            else: 
                print "Found subscription for %s" % options.sub_id
                self._update_subscription(mb, sub, config, options)
        else: 
            self.print_usage()
            return 1

plugins.register(UpdateSubscriptionCommand(), COMMANDLINE_PLUGIN)

class TrimCommand(MailboxesCommand):

    command_name = 'trim'
    description = 'trim items in a set of mailboxes'

    def setup_options(self, parser):
        MailboxesCommand.setup_options(self, parser)
        parser.add_option('--days', type="int", dest="days", help="delete items older than this number of days")

    def _do_update(self, mailboxes, config, options):
        if not options.days: 
            self.print_usage()
            return 1

        delta = timedelta(days=options.days)
        for mb in mailboxes:
            deletes = trim_mailbox(mb, delta)
            print "Deleted %d items from %s" % (deletes, mb.name)
        
plugins.register(TrimCommand(), COMMANDLINE_PLUGIN)





