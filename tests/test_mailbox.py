from helpers import *

def test_mailbox_count():
    """
    create a mailbox
    add some messages
    count messages, make sure count is accurate
    """
    from radarpost.mailbox import Message
    
    # create a mailbox 
    mb = create_test_mailbox()
    # make sure there are no items in the mailbox
    count = 0
    for r in mb.view(Message.by_timestamp, group=False):
        count += r.value
    assert count == 0


    items_to_insert = 44
    for i in range(items_to_insert):
        Message().store(mb)

    count = 0
    for r in mb.view(Message.by_timestamp, group=False):
        count += r.value
    assert count == items_to_insert

def test_mailbox_trim(): 
    """
    create a mailbox
    add some dated messages 
    trim out old messages
    check correct messages remain
    check old messages are not present
    """
    from datetime import datetime, timedelta
    from radarpost.mailbox import Message, trim_mailbox
    
    # create a mailbox 
    mb = create_test_mailbox()
    
    # insert 10 messages, each one day older 
    # than the next, starting with today.
    now = datetime.utcnow()
    delta = timedelta(days=-1)
    cur = now
    messages = []
    for i in range(10):
        m = Message()
        m.timestamp = cur
        m.store(mb)
        messages.append(m)
        cur += delta
        
    # all messages should be in the mailbox now
    for m in messages: 
        assert m.id in mb
    
    # get rid of messages older than 5 days
    trim_mailbox(mb, timedelta(days=5))
    
    for m in messages[:5]: 
        assert m.id in mb
    for m in messages[5:]:
        assert not m.id in mb

    
    