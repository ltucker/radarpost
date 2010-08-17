from couchdb import Server
from datetime import datetime
import logging
import traceback
from radarpost.mailbox import Subscription, iter_mailboxes
from radarpost.feed.docs import FeedSubscription, FEED_SUBSCRIPTION_TYPE
from radarpost.feed.parser import parse, InvalidFeedError
from radarpost.feed.update import update_feed_subscription

log = logging.getLogger(__name__)

def poll_feed(mb, sub, http, force=False):
    log.info("polling %s" % sub.url)
    did_update, status, count = _try_poll_feed(mb, sub, http, force)

    if not did_update:
        # update the subscription info to 
        # indicate that we tried.
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

def _try_poll_feed(mb, sub, http, force):
    try:
        # fetch the feed
        response, content = http.request(sub.url)

        if response.fromcache:
            if not force:
                log.info("feed %s => (cached response)" % sub.url)
                return False, Subscription.UNCHANGED, 0
            else:
                log.info("feed %s => (cached response) *forcing update" % sub.url)

        log.info("feed %s => status %d" % (sub.url, response.status)
        if  response.status != 200:
            return False, Subscription.ERROR, 0

        feed = parse(content, sub.url)
        count = update_feed_subscription(mailbox, subscription, feed)
        return True, Subscription.OK, count

    except InvalidFeedError:
        log.error("feed %s => parse error" % sub.url)
        return False, Subscription.ERROR, 0
    except:
        log.error("feed %s: unexpected error: %s" % (sub.url, traceback.format_exc())
        return False, Subscription.ERROR, 0


if __name__ == '__main__':
    import sys
    from httplib2 import Http

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        log.error("usage %s <couchdb address>" % sys.argv[0])
        sys.exit(0)

    couchdb = Server(sys.argv[1])
    http = Http()
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
