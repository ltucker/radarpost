=================
Configuration
=================

apps 

=================
App Organization 
=================

urls  
templates 
static


=================
User / Login API
=================

User Identification <userid>
==============================
^[a-zA-Z0-9_]{0, 64}$

String used to identify a particular user.  Publicly viewable
identifiers may vary from this identifier.


POST /login
============
login to a session.  body varies on content-type header of 
submission. Accepts form submission or json.

application/x-json, eg: 
{'username': <username>, 'password': <password>}

x-www-form-urlencoded, eg:
username=<username>&password=<password>

parameters:
-----------
username - the username of the user logging in 
password - the password of the user logging in
next     - (optional) if specified, send a redirect 
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

Body
----
json structure with user info
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

application/x-json, eg: 
{'username': <username>, 'password': <password>, 'password2': <password>}

x-www-form-urlencoded, eg:
username=<username>&password=<password>&password2=<password>

parameters:
-----------
username  - the username of the user to create
password  - (optional) the password for the user, if specified must provide password2
password2 - (optional) repeat the password for the user 

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
Body
----
json structure with user info
{'userid': <userid>, name: <viewable identifier>, ...}

Results
-------
200 - user exists, info in body
404 - user does not exist



PUT /user/<userid>
==================================
create a new user with username=<userid> with the info specified

body varies on content-type header of 
submission. Accepts form submission or json.

application/x-json, eg: 
{'password': <password>, 'password2': <password>}

x-www-form-urlencoded, eg:
password=<password>&password2=<password>

parameters:
-----------
password  - (optional) the password for the user, if specified must provide password2
password2 - (optional) repeat the password for the user 

if password is not specified, the user will be unable to login via the username/password
authentication method until a password is provided.

Results
-------
201 - user was created successfully
409 - user already existed


POST /user/<userid>
===================
update the info of an existing user

body varies on content-type header of 
submission. Accepts form submission or json.

application/x-json, eg: 
{'password': <password>, 'password2': <password>}

x-www-form-urlencoded, eg:
password=<password>&password2=<password>

parameters:
-----------
password  - (optional) the password for the user, if specified must provide password2
password2 - (optional) repeat the password for the user 


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
^[a-z0-9_]{0, 128}$

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


POST /<mbid>
============
try to create a mailbox at the url specified.  

Body
-------
body of post may contain a json document initial details about
the mailbox of the form:

{'name': "The displayed title of the mailbox"}

Results
--------
201 - if successfully created
409 - the mailbox already exists

DELETE /<mbid>
==============
destroy the mailbox at mbid

Results
---------

200 - successfully deleted
404 - mailbox did not exist