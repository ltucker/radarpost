=================
REST API
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