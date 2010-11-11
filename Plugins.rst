==================
Plugin System
==================

radarpost uses a very basic plugin system to rig together different 
components.  The rigging is housed in the top-level plugins module.

A plugin can be any python object, which of course includes classes, 
functions as well as any value (read: anything)  


Registering a plugin
--------------------

plugins are attached to a particular 'slot' identified (usually) by a string.

>>> import plugins
>>>
>>> MY_PLUGIN_SLOT = 'my.plugin'
>>> plugins.register(42, MY_PLUGIN_SLOT)

Great, 42 is now a part of the plugin slot 'my.plugin' and anything
that uses 'my.plugin' will 

Getting plugins
---------------

to get things plugged into a slot, use the 'get' function of the plugins module.

>>> for plugin in plugins.get(MY_PLUGIN_SLOT):
>>>    print plugin
42

==================================
Mailbox Design Document Plugins
==================================
slot: mailbox.DESIGN_DOC_PLUGIN

This plugin slot accepts a dictionary representing a design document.  Objects in the slot are added as design documents to all mailboxes that are created / synced.

eg: 

DESIGN_DOC = {
    '_id': '_design/mailbox',
    'views': {
        'messages_by_timestamp': {
            'map':
                """
                function(doc) {
                    if (doc.type == 'message') {
                        emit(doc.timestamp, {'_rev': doc._rev});
                    }
                }
                """,
# ...
}}}
plugins.register(DESIGN_DOC, DESIGN_DOC_PLUGIN)

===============================================
Document Subtype plugins 
===============================================
slot: <Type>.SUBTYPE_PLUGIN

This plugin is used to register subtypes of a Document class, eg a FeedSubscription subtype of Subscription.  It allows the correct subclass to be constructed when retrieving a mixed set of results from a view, or retrieving a Document by id without knowledge of its specific subtype.  

The slot accepts functions that can create subtypes given a subtype name.  If a plugin cannot handle a particular subtype, it should return None.  A Document type with subtypes should inherit from mailbox.DowncastDoc and declare SUBTYPE_PLUGIN (the plugin id) and SUBTYPE_FIELD (a field in the document that is used to select the subtype and passed to the plugin functions)

eg: 

Subscription looks something like this: 

class Subscription(DowncastDoc):

    type = TextField(default=SUBSCRIPTION_TYPE)
    subscription_type = TextField()

    # ...
    
    SUBTYPE_PLUGIN = 'radar.mailbox.subscription_subtype'
    SUBTYPE_FIELD = 'subscription_type'

# a FeedSubscription subtype is registered like this:

@plugins.plugin(Subscription.SUBTYPE_PLUGIN)
def create_feedsub(typename):
    if typename == FEED_SUBSCRIPTION_TYPE: 
        return FeedSubscription()
    return None


===============================
Config INI parser
===============================

slot: config.CONFIG_INI_PARSER_PLUGIN

This plugin id is used to register configuration validators / manipulators
that can check and parse the types of configuration values read from 
the configuration ini file.

the parser should accept a dict and raise an exception
if any illegal configuration is found.  The parser is 
free to manipulate the configuration as needed.

eg: 

#
# parse the http port as an integer
#
@plugins.plugin(CONFIG_INI_READER_PLUGIN)
def http_port_conf(config):
   if 'http.port' in config: 
      config['http.port'] = int(config['http.port'])
      
============================
Command Line / Shell Plugins
============================

slot: main.COMMAND_LINE_PLUGIN

This plugin id is used to expose administrative commands available at the 
command line as 'radarpost <command>' and in the shell as 'cmds.<command>'.

The plugin accepts classes with the interface below, but many commands
may be simplified by inheriting from main.BasicCommand. 
see cli.basic.ShowConfigCommand for a basic example.

class SomeCommand(object):

    command_name = "<name used on command line and shell>"
    description = "<a brief description of the command used in help>"
    
    def __init__(config): 
        """
        called to initialize the command with the current 
        configuration which defines the context in that the
        command will run in. 
        """
    
    def print_usage():
        """
        Called to print out an informative description of 
        the command and its arguments.  Used for example
        during help, when an invalid argument has been
        given or when an argument is missing.
        """

    def setup_options(parser):
        """
        called to set up any commmand line arguments specific
        to this command.  parser is an optparse OptionParser.
        """

    def run(args, options): 
        """
        called when invoked from the command line, should parse 
        the command line options in any way needed and invoke self.__call__
        
        args - any non-flag arguments specified at the command line
        options - the result of the optparse options parsing.
        """
        
    def __call__(...):
        """
        called to invoke the actual command.  This is exposed directly 
        in the shell.  
        """

==================================
Subscription Update Handler 
==================================

slot: agent.plugins.SUBSCRIPTION_UPDATE_HANDLER

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

=======================================
Atom Renderer Plugin
=======================================

slot: web.api.controller.ATOM_RENDERER_PLUGIN

This slot represents plugins that can render a Message
into an Atom entry.  

Most types can be handled by just creating a template called 
radar/atom/entry/<message_type>.xml

Specifically, the slot is filled with callables that accept a Message 
and a Request, and produce a zero argument callable returning the text
of an atom entry representing the Message.  If the Message cannot be handled,
None should be returned. eg: 

@plugin(ATOM_RENDERER_PLUGIN)
def _render_empty(message, request):
    if message.message_type != 'empty':
        return None
        
    def render(): 
        return "<entry></entry>"
    return render

=======================================
HAtom Renderer Plugin
=======================================

slot: web.radar_ui.controller.HATOM_RENDERER_PLUGIN

This slot represents plugins that can render a Message
into an HAtom entry (html)

Most types can be handled by just creating a template called 
radar/hatom/entry/<message_type>.html

Specifically, the slot is filled with callables that accept a Message 
and a Request, and produce a zero argument callable returning the html
representing the Message.  If the Message cannot be handled,
None should be returned. eg: 

@plugin(HATOM_RENDERER_PLUGIN)
def _render_empty(message, request):
    if message.message_type != 'empty':
        return None

    def render(): 
        return '<div class="hentry"></div>'
    return render
