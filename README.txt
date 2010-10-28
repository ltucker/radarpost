RadarPost
=========

RadarPost is a web based feed aggregator that uses Python and CouchDB.


Quickstart
==========

This quickstart assumes you have virtualenv and pip. 
Start by pulling in radarpost and its deps::

  $ virtualenv radarpost
  $ pip install -Eradarpost -r http://github.com/ltucker/radarpost/raw/master/requirements.txt

If all goes well, activate your environment and fire things up: 

  $ cd radarpost
  $ source bin/activate
  $ radarpost serve
  * serving on 127.0.0.1:9332
  
Point your browser to the URL shown to check things out.  You'll need to create a user, which 
can only be done at the command line currently. 

  $ radarpost create_user <yourname> --admin
  
To see what else is available from the command line, try: 
  
  $ radarpost help
  
