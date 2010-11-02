RadarPost
=========

RadarPost is a web based feed aggregator that uses Python and CouchDB.


Quickstart
==========

This quickstart assumes you have virtualenv and pip and a couchdb running on the standard port.
Start by pulling in radarpost and its deps::

  $ virtualenv radarpost
  $ pip install -Eradarpost -r http://github.com/ltucker/radarpost/raw/master/requirements.txt

If all goes well, activate your environment and fire things up.  If you need to adjust the settings
first, edit src/radarpost/radar.ini::

  $ cd radarpost
  $ source bin/activate
  $ radarpost serve -Csrc/radarpost/radar.ini
  * serving on 127.0.0.1:9332
  
Point your browser to the URL shown to check things out.  You'll need to create a user, which 
can only be done at the command line currently. **Note**: unless the configuration is changed, 
this will create a couchdb user in the _users database::

  $ radarpost create_user <yourname> --admin -Csrc/radarpost/radar.ini
  
To see what else is available from the command line, try:: 
  
  $ radarpost help -Csrc/radarpost/radar.ini
  
If you get sick of saying -Csrc/radarpost/radar.ini, you can set the RADAR_CONFIG environment variable thusly::

  $ export RADAR_CONFIG=$PWD/src/radarpost/radar.ini 
  $ radarpost help 
  ... hooray!

Okay, now what?
===============

Well, things are a bit incomplete, but if something cannot be done with the user interface, it may already have an API you can hit with curl, or a command line function to help out.  Here's an example of settings up a new mailbox and getting some feeds in from the command line.

Create a mailbox:: 

  $ curl -v -u<user>:<pass> -XPUT http://localhost:9332/funfeeds
  ... 
  < HTTP/1.1 201 Created
  ...
  
Import feeds from an OMPL file::

    $ curl -v -u<user>:<pass> -XPOST http://127.0.0.1:9332/funfeeds/subscriptions.opml --data @feeds.opml
    ...
    < HTTP/1.1 200 OK
    ...
    {"deleted": 0, "errors": 0, "imported": 428}

Now update the feeds::

    $ radarpost update funfeeds -Csrc/radarpost/radar.ini
    
    INFO:radarpost.agent.feed:polling http://www.example.com/feeds/12
    ...
    
    
Running Tests
=============

To run the tests, it is recommended that you install nose::

    $ cd radarpost
    $ source bin/activate
    $ pip install nose

To run the tests, run `nosetests` from the radarpost source folder::

    $ cd src/radarpost
    $ nosetests
    ...
    

