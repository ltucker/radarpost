from couchdb import Server
from datetime import datetime
import logging
import traceback
from radarpost.mailbox import Subscription, iter_mailboxes
from radarpost.feed.docs import FeedSubscription, FEED_SUBSCRIPTION_TYPE
from radarpost.feed.parser import parse, InvalidFeedError


log = logging.getLogger(__name__)

def poll_feed(mb, sub, http, force=False):
    log.info("polling %s" % sub.url)
    
    # fetch the feed
    response, content = http.request(sub.url)

    if response.fromcache:
        sub.last_update = datetime.now()
        sub.status = "Unchanged"
        sub.store(mb)
    elif response.status != 200:
        sub.late_update = datetime.now()
        sub.status = "Error %d" % response.status 
        sub.store(mb)
        return

    if not response.fromcache or force == True:
        # parse it 
        try: 
            feed = parse(content, sub.url)
            update_feed_subscription(mb, sub, feed)
        except InvalidFeedError:
            sub.last_update = datetime.now()
            sub.status = "Invalid feed content"
        except:
            sub.status = "Internal error"
            sub.last_update = datetime.now()
            log.error("Unexpected error updating %s: %s" % (sub.url, traceback.format_exc())
        

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
