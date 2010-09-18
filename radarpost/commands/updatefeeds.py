from couchdb import Server, ResourceConflict
from datetime import datetime
import logging
import traceback
from radarpost.mailbox import *
from radarpost.feed import *

log = logging.getLogger(__name__)

def poll_feed(mb, sub, http):
    """
    poll a single feed in a single mailbox.
    
    mb - the mailbox to update 
    sub - the subscription document in the mailbox
    http - an http client (httplib2)
    force - if true, try to update even if a previously 
            encountered result is fetched.
    """
    log.info("polling %s" % sub.url)
    did_update, status, count = _try_poll_feed(mb, sub, http, force)

    if did_update:
        return

    # no update performed, update the subscription info to 
    # indicate that we tried...
    now = datetime.utcnow()
    while(sub.last_update is None or sub.last_update < now):
        try:
            sub.status = status
            sub.last_update = now
            sub.store(mb)
            break
        except ResourceConflict:
            # oops changed since we started, reload it.
            try:
                subscription = mailbox[subscription.id]
            except ResourceNotFound:
                # deleted from underneath us, bail out.
                break
    return 0

def _try_poll_feed(mb, sub, http, force):
    try:
        # fetch the feed
        response, content = http.request(sub.url)
        log.info("feed %s => status %d" % (sub.url, response.status))
        if response.status != 200:
            return False, Subscription.ERROR, 0

        # try to reject update based on content digest...
        digest = hashlib.md5()
        digest.update(content)
        digest = digest.hexdigest()
        
        if digest == sub.last_digest:
            if not force:
                log.info("mailbox %s <= feed %s: unchanged since last update" % (mb.name, sub.url))
                return False, Subscription.UNCHANGED, 0
            else:
                log.info("mailbox %s <= feed %s unchanged since last update (*forcing update)" % (mb.name, sub.url))

        feed = parse(content, sub.url)
        count = update_feed_subscription(mailbox, subscription, feed,
                                         subscription_delta={'last_digest': digest})
        return True, Subscription.OK, count

    except InvalidFeedError:
        log.error("mailbox %s <= feed %s: parse error" % (mb.name, sub.url))
        return False, Subscription.ERROR, 0
    except:
        log.error("mailbox %s <= feed %s: unexpected error: %s" % (mb.name, sub.url, traceback.format_exc()))
        return False, Subscription.ERROR, 0

def main(argv):
    from httplib2 import Http
    from optparse import OptionParser 

    logging.basicConfig(level=logging.INFO)

    parser = OptionParser()
    parser.add_option('--couchdb', 
                      dest='couchdb',
                      default='http://localhost:5984',
                      help='address of couchdb')
    parser.add_option('--cache',
                      dest='http_cache',
                      default=None,
                      help='directory to use for caching')

    options, args = parser.parse_args(argv)

    couchdb = Server(options.couchdb)
    http = Http(options.http_cache)
    http.timeout = 15 
    http.force_exception_to_status_code = True

    for mb in iter_mailboxes(couchdb):
        log.info("Updating %s" % mb.name)
        feed_count = 0
        for sub in FeedSubscription.view(mb, Subscription.by_type,
                                          startkey=FEED_SUBSCRIPTION_TYPE,
                                          endkey=FEED_SUBSCRIPTION_TYPE,
                                          include_docs=True):
            poll_feed(mb, sub, http)
            feed_count += 1
        log.info("Finished %s - %d updated" % (mb.name, feed_count))

if __name__ == '__main__':
    import sys
    main(sys.argv)