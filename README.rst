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

Okay, now what??
================

Now you can visit your site and login with the user you created above.  You should be able to create new aggregations and import feeds through the user interface.  

Updating
========

Updates are still performed manually, you can update everything by running::

    $ radarpost update --all
    ...
    INFO:radarpost.agent.feed:polling http://www.example.com/feeds/12
    ...

You may find it useful to call this periodically using cron.


Using the API
=============

You can find more detailed information in the included API.rst.  Here is a quick example to get you started:

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
    
