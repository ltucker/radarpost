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

