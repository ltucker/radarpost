=================
User / Login API
=================


User Identification <userid>
==============================
^[a-zA-Z0-9\_]{0, 64}$

String used to identify a particular user.  Publicly viewable
identifiers may vary from this identifier.


HTTP Basic Auth
================
Login credentials may be specified on a per-request basis using http basic
authentication. http://en.wikipedia.org/wiki/Basic_access_authentication


POST /login
============
login to a session and obtain a cookie.  body varies on
content-type header of submission. Accepts form submission or json

application/x-json, eg::

    {'username': <username>, 'password': <password>}

x-www-form-urlencoded, eg::

    username=<username>&password=<password>

parameters:
-----------
username
  the username of the user logging in
password
  the password of the user logging in
next (optional)
  if specified, send a redirect
  to this url on successful login.

Results
-------
Cookie identifying session will be set or re-set,
previous session (if any) will be invalidated.

200 - successful login (next_page not specified)
302 - successful login (next_page specified)
401 - authentication failure


POST /logout
=============

Logout current user and reset session.
body is ignored.

Results
--------
previous session (if any) will be invalidated.

200 - successfully logged out


GET /user
=========
retrieve info for currently logged in user.

Response Body
--------------
json structure with user info::

    {'is_anonymous': <boolean>, ['userid': <userid>], [name: <viewable identifier>], ...}

Results
-------
200 - user exists, info in body
404 - user does not exist


POST /user
==================================
create a new user with the info specified

body varies on content-type header of
submission. Accepts form submission or json.

application/x-json, eg::

    {'username': <username>, 'password': <password>, 'password2': <password>}

x-www-form-urlencoded, eg::

    username=<username>&password=<password>&password2=<password>

parameters:
-----------
username
    the username of the user to create
password (optional) 
    the password for the user, if specified must provide password2
password2 (optional)
    repeat the password for the user

if password is not specified, the user will be unable to login via the username/password
authentication method until a password is provided.

Results
-------
201 - user was created successfully
409 - user already existed


HEAD /user/<userid>
====================

Results
-------
200 - user exists
404 - user does not exist



GET /user/<userid>
==================
Response Body
-------------
json structure with user info::

    {'userid': <userid>, name: <viewable identifier>, ...}

Results
-------
200 - user exists, info in body
404 - user does not exist



PUT /user/<userid>
==================================
create a new user with username=<userid> with the info specified

Request Body
------------
body varies on content-type header of
submission. Accepts form submission or json.

application/x-json, eg::

    {'password': <password>, 'password2': <password>}

x-www-form-urlencoded, eg::

    password=<password>&password2=<password>

parameters:
-----------
password (optional)
    the password for the user, if specified must provide password2
password2 (optional)
    repeat the password for the user

if password is not specified, the user will be unable to login via the username/password
authentication method until a password is provided.

Results
-------
201 - user was created successfully
409 - user already existed


POST /user/<userid>
===================
update the info of an existing user


Request Body
------------
body varies on content-type header of
submission. Accepts form submission or json.

application/x-json, eg::

    {'password': <password>, 'password2': <password>}

x-www-form-urlencoded, eg::

    password=<password>&password2=<password>

parameters:
-----------
password (optional)
    the password for the user, if specified must provide password2
password2 (optional)
    repeat the password for the user


Results
-------
200 - success

DELETE /user/<userid>
=====================

delete a user

Results
-------
200 - success
404 - user did not exist

=================
Mailbox API
=================


Mailbox identifier <mbid>
=========================
^[a-z0-9\_]{0, 128}$

* it is all lowercase
* letters, numbers and _
* max length 128

HEAD /<mbid>
============
test the existence of a mailbox at the url given

Results
--------
200 - the mailbox exists
404 - the mailbox does not exist

GET /<mbid>
============
test the existence of a mailbox at the url given

Results
--------
200 - the mailbox exists
404 - the mailbox does not exist


PUT /<mbid>
============
try to create a mailbox at the url specified.

PUT Body
--------
body of post may contain a json document initial details about
the mailbox of the form::

    {'name': "The displayed title of the mailbox"}

Results
--------
201 - if successfully created
409 - the mailbox already exists

POST /<mbid>
============
update a mailbox at the url specified.

Request Body
------------
body of post may contain a json document initial details about
the mailbox of the form::

    {'name': "The displayed title of the mailbox"}

Results
--------
200 - if successfully updated
404 - the mailbox does not exist


DELETE /<mbid>
==============
destroy the mailbox at mbid

Results
--------

200 - successfully deleted
404 - mailbox did not exist


=================
Messages API
=================

DELETE /<mbid>/items/<message_id>
=================================

delete a message in a mailbox

Results
--------
200 - the message was deleted
404 - the mailbox or the message did not exist


=================
Subscriptions API
=================

GET /<mbid>/subscriptions.opml
===============================
retrieve an OPML document representing all Feed type subscriptions

Response Body
-------------
OPML feed list

PUT /<mbid>/subscriptions.opml
==============================
replace all subscriptions with only those in the OPML document found
in the request body.

Request Body
------------
OPML feed list

POST /<mbid>/subscriptions.opml
================================
Add subscriptions in the OPML document found in the
request body.

Request Body
------------
OPML feed list


GET /<mbid>/subscriptions.json
=================================
retrieve json structure representing subscriptions

Response Body
-------------
of the form:: 

    [{'slug': <sub id>, 'type': <subscription type>, 'title': <title>, <... type specific>}, ...]

eg::
    
    [{'slug': '7c43fb2bc54cec30c98edbf6a31ad535',
      'type': 'feed',
      'title': 'Example Feed',
      'url': 'http://www.example.com/feeds/1'}, ...]

Results
--------
404 - the mailbox 'mbid' does not exist

POST /<mbid>/subscriptions.json
================================

create a subscription in the mailbox 'mbid'

Request Body
------------

of the form::

    {'type': <subscription type>, 'title': <title>, <... type specific>}

eg::
    
    {'type': 'feed',
     'title': 'Example Feed',
     'url': 'http://www.example.com/feeds/1'}

Response Body
---------------
{'slug': <new slug>}

Results
-------
201 - the subscription was created


HEAD /<mbid>/subscriptions/<subid>
===================================
test the existence of a subscription at the url given

Results
--------
200 - the subscription exists
404 - the mailbox or the subscription does not exist

GET /<mbid>/subscriptions/<subid>
==================================
get info about a particular subscription

Response Body
-------------
of the form::

    {'slug': <sub id>, 'type': <subscription type>, 'title': <title>, <... type specific>}
    
eg::
    
    {'slug': '7c43fb2bc54cec30c98edbf6a31ad535',
      'type': 'feed',
      'title': 'Example Feed',
      'url': 'http://www.example.com/feeds/1'}

Results
--------
200 - the subscription exists
404 - the mailbox or subscription does not exist


DELETE /<mbid>/subscriptions/<subid>
====================================
delete the subscription at the url given

Results
--------
200 - the subscription was deleted
404 - the mailbox or the subscription did not exist

POST /<mbid>/subscriptions/<subid>
==================================
update subscription information

body varies on content-type header of
submission. Accepts form submission or json.

application/x-json, eg::

    {'title': 'New Title'}

x-www-form-urlencoded, eg::

    title=New%20Title

Response Body
-------------
of the form::

    {'slug': <sub id>, 'type': <subscription type>, 'title': <title>, <... type specific>}

Results
--------
200 - success
404 - the mailbox or subscription does not exist
400 - update failed, invalid info

===============
Feed Search API
=============== 

GET /feedsearch/feed 
====================

Checks for an Atom, RSS etc feed document directly available at the url specified.

parameters: 
url - the url to chek 

Response Body
-------------

of the form: 
{"links": [{"url": "http://example.com/feed/1", "title": "The Feed's title"}]}


GET /feedsearch/html
====================

Search a web page for links to feeds.  Looks for link rel="alternate"
with appropriate type.  Titles returned are those listed in the html
not the feed itself and are often not provided.

Response Body
------------

list of the form: 
{"links": [{"url": "http://www.example.org/feed/2", "title": "Feed Title"}, ...]}

POST /feedsearch/opml
=====================

Find the feed links listed in an OPML file.  Titles are taken from 
those listed in the OPML file.

Request Body 
------------
The request may be made by posting a form with multipart/formdata, a field "opmlfile" should contain the opml data file upload.


Response Body 
-------------

of the form:
{ "links": [{"url": "http://www.example.org/feed/2", "title": "Feed Title"}]}
  
if a multipart/formdata request is POSTed, the result is wrapped in html 
to facilitate asynchronously loading the result into an iframe using a 
browser, eg:

<html><head></head><body>
{&#34;links&#34;: [{&#34;url&#34;: &#34;http://example.com/feeds/1&#34;, &#34;title&#34;: &#34;Example Feed&#34;}]}
</body></html>
