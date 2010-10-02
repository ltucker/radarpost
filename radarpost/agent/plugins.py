SUBSCRIPTION_UPDATE_HANDLER = 'radarpost.agent.plugins.subscription_update_handler'
"""
Register methods that handle updating subscriptions. 

return True if the subscription was handled, False if the subscription was not
handled. throw exceptions for errors. 

method signature is: 
update(mailbox, subscription, config) => bool

eg: 

@plugin(SUBSCRIPTION_UPDATE_HANDLER)
def update_twizzle(mb, sub, config): 
    if sub.subscription_type != 'twizzle': 
        return False
    # contact twizzle.org
    # ...
    return True
"""