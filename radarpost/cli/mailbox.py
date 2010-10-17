from couchdb import Server, ResourceConflict, ResourceNotFound
from datetime import datetime, timedelta
import logging
import traceback
from radarpost.agent import SUBSCRIPTION_UPDATE_HANDLER
from radarpost.feed import *
from radarpost.mailbox import *
from radarpost.main import COMMANDLINE_PLUGIN, BasicCommand, InvalidArguments
from radarpost import plugins

log = logging.getLogger(__name__)

class MailboxHelper(object):

    def _get_mailbox(self, slug):
        couchdb = Server(self.config['couchdb.address'])
        prefix = self.config['couchdb.prefix']

        name = prefix + slug
        if not name in couchdb: 
            raise InvalidArguments('Mailbox "%s" does not exist' % slug)

        mb = couchdb[name]
        if not is_mailbox(mb): 
            raise InvalidArguments('database %s is not a mailbox.' % name)

        return mb

    def _get_mailboxes(self, slugs=None, get_all=False):
        if get_all == True and slugs and len(slugs) > 0:
            raise InvalidArguments("Cannot specify all and list of mailboxes.")

        couchdb = Server(self.config['couchdb.address'])
        prefix = self.config['couchdb.prefix']

        if get_all:
            return iter_mailboxes(couchdb, prefix=prefix)
        else:
            selected = []
            for slug in slugs:
                mb = self._get_mailbox(slug)
                selected.append(mb)
            if len(selected) == 0: 
                raise InvalidArguments('You must specify at least one mailbox.')
            return selected

    def _update_subscription(self, mailbox, sub):
        for handler in plugins.get(SUBSCRIPTION_UPDATE_HANDLER):
            if handler(mailbox, sub, self.config) == True:
                return True
        log.info('%s: no update handler for subscription "%s" of type "%s"' % 
                 (mb.name, sub.id, sub.subscription_type))
        return False

class MailboxesCommand(BasicCommand, MailboxHelper):

    @classmethod
    def setup_options(cls, parser):
        parser.set_usage(r"%prog " + "%s [mailbox] [mailbox] ... [options]" % cls.command_name)
        parser.add_option('--all', action='store_true', dest="update_all", default=False, help="apply to all mailboxes")
    
    def run(self, args, options):
        kw = self.clean_options(options)
        try:
            self(mailboxes=args, **kw)
        except TypeError:
            self.print_usage()

    
class UpdateSubscriptionsCommand(MailboxesCommand):

    command_name = 'update'
    description = 'update all subscriptions in a set of mailboxes'

    def __call__(self, mailboxes=None, update_all=False):
        """
        update all subscriptions in the given list of mailboxes.
        mailboxes - list of mailboxes to update (slugs)
        update_all - update all mailboxes
        """
        for mb in self._get_mailboxes(mailboxes, get_all=update_all):
            for sub in Subscription.view(mb, Subscription.by_type, include_docs=True):
                try:
                    self._update_subscription(mb, sub)
                except: 
                    log.error('%s: error updating subscription "%s" of type "%s": %s' % 
                        (mb.name, sub.id, sub.subscription_type, traceback.format_exc()))

plugins.register(UpdateSubscriptionsCommand, COMMANDLINE_PLUGIN)

class UpdateSubscriptionCommand(BasicCommand, MailboxHelper):
    
    command_name = 'update_sub'
    description = 'update a particular subscription in a mailbox'

    @classmethod
    def setup_options(cls, parser):
        parser.set_usage(r"%prog " + "%s mailbox [options]" % cls.command_name)
        parser.add_option('--id', dest="sub_id", help="specify subscription by id")
        parser.add_option('--feed', dest="feed_url", help="specify subscription by feed url")

    def __call__(self, mailbox, sub_id=None, feed_url=None):
        """
        update the specified subscription in the mailbox specified 
        mailbox - the slug of the mailbox to update
        sub_id - specify subscription by id
        feed_url - specify subscription by feed_url
        """
        mb = self._get_mailbox(mailbox)
        if mb is None:
            return 1
        if feed_url is not None and sub_id is not None:
            raise InvalidArguments("You may only specify one subscription")

        if feed_url is not None:
            params = {
                'include_docs': True,
                'startkey': feed_url,
                'endkey': feed_url
            }
            sub = None
            for sub in Subscription.view(mb, FeedSubscription.by_url, **params):
                break
    
            if sub is None:
                print "No subscription with url %s in mailbox %s" % (feed_url, mb.name)
            else: 
                print "Found subscription for %s (%s)" % (feed_url, sub.id)
                self._update_subscription(mb, sub)
        elif sub_id is not None:
            sub = Subscription.load(mb, sub_id)
            if sub is None or not sub.type == SUBSCRIPTION_TYPE: 
                print "No subscription with id %s found in mailbox %s" % (sub_id, mb.name)
            else: 
                print "Found subscription for %s" % sub_id
                self._update_subscription(mb, sub)
        else:
            raise InvalidArguments("You must specify a subscription")

plugins.register(UpdateSubscriptionCommand, COMMANDLINE_PLUGIN)

class TrimCommand(MailboxesCommand):

    command_name = 'trim'
    description = 'trim items in a set of mailboxes'

    @classmethod
    def setup_options(cls, parser):
        super(TrimCommand, cls).setup_options(parser)
        parser.add_option('--days', type="int", dest="days", help="delete items older than this number of days")

    def __call__(self, mailboxes=None, days=None, update_all=False):
        """
        remove articles older than a certain age
        mailboxes - list of mailboxes to trim (by slug)
        update_all - update all mailboxes
        days - specify the maximum age in days
        """
        if days is None:
            raise InvalidArguments("You must specify the maximum age")

        delta = timedelta(days=days)
        for mb in self._get_mailboxes(mailboxes, get_all=update_all):
            deletes = trim_mailbox(mb, delta)
            print "Deleted %d items from %s" % (deletes, mb.name)
plugins.register(TrimCommand, COMMANDLINE_PLUGIN)
