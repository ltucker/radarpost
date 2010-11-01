from couchdb import Server, ResourceConflict, ResourceNotFound
from datetime import datetime
import hashlib
from httplib2 import Http
import logging
import traceback

from radarpost.feed import FEED_SUBSCRIPTION_TYPE, parse, update_feed_subscription, InvalidFeedError
from radarpost.mailbox import Subscription
from radarpost import plugins
from radarpost.agent.plugins import SUBSCRIPTION_UPDATE_HANDLER

log = logging.getLogger(__name__)

def poll_feed(mb, sub, http, force=False):
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
        log.info("feed %s => created %d new items" % (sub.url, count))
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
            return False, Subscription.STATUS_ERROR, 0

        # try to reject update based on content digest...
        digest = hashlib.md5()
        digest.update(content)
        digest = digest.hexdigest()
        
        if digest == sub.last_digest:
            if not force:
                log.info("mailbox %s <= feed %s: unchanged since last update" % (mb.name, sub.url))
                return False, Subscription.STATUS_UNCHANGED, 0
            else:
                log.info("mailbox %s <= feed %s unchanged since last update (*forcing update)" % (mb.name, sub.url))

        feed = parse(content, sub.url)
        count = update_feed_subscription(mb, sub, feed, subscription_delta={'last_digest': digest})
        return True, Subscription.STATUS_OK, count

    except InvalidFeedError:
        log.error("mailbox %s <= feed %s: parse error" % (mb.name, sub.url))
        return False, Subscription.STATUS_ERROR, 0
    except KeyboardInterrupt:
        raise
    except:
        log.error("mailbox %s <= feed %s: unexpected error: %s" % (mb.name, sub.url, traceback.format_exc()))
        return False, Subscription.STATUS_ERROR, 0

@plugins.plugin(SUBSCRIPTION_UPDATE_HANDLER)
def poll_feed_sub(mb, sub, config):
    if sub.subscription_type != FEED_SUBSCRIPTION_TYPE:
        return False
    
    # sweet, go ahead...
    http = Http(config.get('http_cache', None))
    http.timeout = 15 
    http.force_exception_to_status_code = True
    poll_feed(mb, sub, http)
    return True
