Welcome to EZGmail's documentation!
=======================================


About
=====

EZGmail is a Python module that makes it simple to use Gmail's API.

Installation
============

``pip install ezgmail``

You must also sign up for a Gmail account at https://gmail.com/. Then, go to
https://developers.google.com/gmail/api/quickstart/python/, click the **Enable the Gmail API** button on that page,
and fill out the form that appears.

After you've filled out the form, the page will present a link to the *credentials.json file*, which you'll need to
download and place in the same folder as your *.py* file. The *credentials.json* file contains the Client ID and
Client Secret information, which you should treat the same as your Gmail password and not share with anyone else.

Make sure you set your current working directory to the same folder
that *credentials.json* is in and that you're connected to the internet. Running
**import ezgmail** (which calls the **ezgmail.init()** function) will open your browser to a Google sign-in page.

Enter your Gmail address and password. The page may warn you "This app
isn't verified," but this is fine; click **Advanced** and then **Go to Quickstart
(unsafe)**. (If you write Python scripts for others and don't want this warning
appearing for them, you'll need to learn about Google's app verification
process, which is beyond the scope of this documentaiton.) When the next page
prompts you with "Quickstart wants to access your Google Account," click
**Allow** and then close the browser.

A *token.json* file will be generated to give your Python scripts access to
the Gmail account you entered. The browser will only open to the login
page if it can't find an existing token.json file. With *credentials.json* and *token.json*,
your Python scripts can send and read emails from your Gmail account
without requiring you to include your Gmail password in your source code.


Quickstart
==========

To log in to your Gmail account, simple import EZGmail after setting up the *credentials.json* and *token.json* files:

``>>> import ezgmail``

If you'd like to log in as a different user (based on different *credentials.json* and *token.json* files), call
``ezgmail.init()`` and pass the filenames for the credential and token files you generated.

``>>> ezgmail.init(tokenFile='token.json', credentialsFile='credentials.json')``

At this point, the ``EMAIL_ADDRESS`` global variable will contain a string of the logged in user, and ``LOGGED_IN`` is
set to ``True``. (Otherwise, they are set to ``None`` and ``False``, respectively.)

.. code-block::

    >>> ezgmail.EMAIL_ADDRESS
    'test.sweigart@gmail.com'
    >>> ezgmail.LOGGED_IN
    True

To send an email from the logged in account, call ``ezgmail.send()``:

``>>> ezgmail.send('recipient@example.com', 'Subject Line', 'Hello, this is the body of the message.')``

To get a list of all the email threads of unread emails, call ``ezgmail.unread()``. This returns a list of
``GmailThread`` objects. Each ``GmailThread`` contains a ``messages`` attribute which is a list of ``GmailMessage``
objects. Each ``GmailMessage`` object has attributes ``sender``, ``timestamp``, ``subject``, ``body``:

.. code-block::

    >>> ezgmail.unread()
    [<GmailThread len=4 snippet='Quickstart was granted access to your Google Account test.sweigart@gmail.com If you did not grant access, you should check this activity and secure your account. Check activity You received this email'>]

    >>> unreadThreads = ezgmail.unread()

    >>> unreadThreads
    [<GmailThread len=4 snippet='Quickstart was granted access to your Google Account test.sweigart@gmail.com If you did not grant access, you should check this activity and secure your account. Check activity You received this email'>]

    >>> thread = unreadThreads[0]

    >>> thread.messages
    [<ezgmail.GmailMessage object at 0x000002B7F1FD8A90>, <ezgmail.GmailMessage object at 0x000002B7F1FD80B8>, <ezgmail.GmailMessage object at 0x000002B7F1FD8A58>, <ezgmail.GmailMessage object at 0x000002B7F1FD8160>]

    >>> thread.messages[0].sender
    'Alice Smith <alice@example.com>'

    >>> thread.messages[0].timestamp
    datetime.datetime(2019, 11, 11, 10, 7, 55)

    >>> thread.messages[0].subject
    'Good to meet you!'

    >>> thread.messages[0].body
    "It was good to meetup!\r\n\r\n\r\nWe should hang out again soon.\r\n"

You can call ``ezgmail.recent()`` to get the recent email threads as a list of ``GmailThread`` objects.

You can search for messages by calling ``ezgmail.search('query string')``, which also returns a list of ``GmailThread``
objects. The query string is exactly the same as you would type in the Gmail search box, and you can use the search
operatives for it too:

    * label:UNREAD
    * from:al@inventwithpython.com
    * subject:hello
    * has:attachment

More search operatives are described at https://support.google.com/mail/answer/7190?hl=en

The API contains complete documentation.

API
===

.. automodule:: ezgmail
    :members:


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


