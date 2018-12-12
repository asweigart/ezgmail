EZGmail
======

A Pythonic interface to the Gmail API that actually works as of Dec 2018.

The Gmail API quickstart doesn't actually seem to work on Python 3 without some adjustments, and the entire documentation is a bit much for someone who just wants to read and send emails from their Gmail account. EZGmail just works.

The Gmail API documentation by Google is available at https://developers.google.com/gmail/api/

Installation
------------

To install with pip, run:

    pip install ezgmail

You will need to download a *credentials.json* file by going to https://developers.google.com/gmail/api/quickstart/python and clicking the **Enable the Gmail API** button (after logging in to your Gmail account).

Once you have the *credentials.json* file, the first time you call ``ezgmail.init()`` it will bring up a window asking you to log in to your Gmail account and allow "Quickstart" to access it. A *token.json* file will be generated which your script can use to access your account.

Future calls to ``ezgmail.init()`` or any other ``ezgmail`` function won't require this token-generating step. The ``gmail.init()`` function is automatically called when any other ``ezgmail`` function is called.


Quickstart Guide
----------------

To see what email address you are sending from, examine ``ezgmail.EMAIL_ADDRESS`` (this is configured by the *token.json* file you're using, and you must first call ``ezgmail.init()`` or some other ``ezgmail`` function first):

    >>> import ezgmail
    >>> ezgmail.init()
    >>> ezgmail.EMAIL_ADDRESS
    'example@gmail.com'

To send an email from your "example@gmail.com" account:

    >>> import ezgmail
    >>> ezgmail.send('recipient@example.com', 'Subject line', 'Body of the email', ['attachment1.jpg', 'attachment2.mp3'])

The ``attachments`` argument is optional, and if you only have one attachment you can just specify the filename string. Also note that Gmail will most likely filter any emails that contain *.exe*, *.zip*, or any other suspicious attachments.

The cc and bcc fields are also optional keyword arguments:

    >>> import ezgmail
    >>> ezgmail.send('recipient@example.com', 'Subject line', 'Body of the email', cc='friend@example.com', bcc='otherfriend@example.com,someoneelse@example.com')

The main classes in ``ezgmail`` are ``GmailThread`` and ``GmailMessage``. A ``GmailThread`` is a chain of emails replying to one another, while a ``GmailMessage`` is an individual email in a thread.

To retrieve unread emails:

    >>> import ezgmail
    >>> unreadThreads = ezgmail.unread()  # Returns a list of GmailThread objects.

The ``summary()`` function is an easy way to print out info on a list of thread or message objects:

    >>> ezgmail.summary(unreadThreads)
    Jon, Al - Remember that old website Hamsterdance? LOL - Dec 09
    Al - This is a test email about gerbils. - Dec 09

If you want this info as a data structure, pass ``printInfo=False`` to ``summary()``:

    >>> ezgmail.summary(unreadThreads, printInfo=False)
    [(['Jon Smith <example@gmail.com>', 'Al Sweigart <al@inventwithpython.com>'], 'Remember that old website Hamsterdance? LOL', datetime.datetime(2018, 12, 9, 13, 29, 17)), (['Al Sweigart <al@inventwithpython.com>'], 'This is a test email about gerbils.', datetime.datetime(2018, 12, 9, 13, 25, 58))]

The ``GmailMessage`` objects of a thread are in the ``messages`` list attribute:

    >>> ezgmail.summary(unreadThreads[0].messages)
    Jon - Remember that old website Hamsterdance? LOL - Dec 09
    Al - Haha that&#39;s awesome! On Sun, Dec 9, 2018 at 1:28 PM Jon Smith &lt;example@gmail.com&gt; wrote: Remember that old website Hamsterdance? LOL - Dec 09

The ``GmailMessage`` objects have ``sender``, ``recipient``, ``subject``, ``body``, and ``timestamp`` attribues:

    >>> msg = unreadThreads[0].messages[0]
    >>> msg.sender
    'Jon Smith <example@gmail.com>'
    >>> msg.recipient
    'Al Sweigart <al@inventwithpython.com>'
    >>> msg.subject
    'Hamsterdance'
    >>> msg.body
    'Remember that old website Hamsterdance? LOL\r\n'
    >>> msg.timestamp
    datetime.datetime(2018, 12, 9, 13, 28, 48)

You can also call the ``recent()`` method to get recent email threads:

    >>> import ezgmail
    >>> recentThreads = ezgmail.recent()
    >>> len(recentThreads)
    22

The ``recent()`` and ``unread()`` functions are just convenient wrappers around ``search()``, which you can pass a query to (just like the query text field in the Gmail.com website):

    >>> import ezgmail
    >>> threads = ezgmail.search('mancala')
    >>> len(threads)
    1
    >>> ezgmail.summary(threads[0])
    Al, Jon - Zanzibar &gt; <b>Mancala</b> is one of the oldest known games to still be widely played today. &gt; <b>Mancala</b> is a generic name for a - Dec 08

The ``search()`` function can accept search operators just like the query text field:

* label:UNREAD
* from:al@inventwithpython.com
* subject:hello
* has:attachment

More are described at https://support.google.com/mail/answer/7190?hl=en

The ``search()``, ``recent()``, and ``unread()`` can also accept a ``maxResults`` keyword argument that is set to 25 by default. This sets an upper limit on how many threads/messages will be returned. API usage quotas are posted at https://developers.google.com/gmail/api/v1/reference/quota (roughly one million requests a day (and 25 per second) for the free tier).


Limitations
-----------

Currently, EZGmail cannot do the following:

* Download attachments from emails.
* Read or set labels. (Including marking emails as read.)
* Sending emails with cc and bcc fields.
* A lot of other basic features. This package is just a start!

Contribute
----------

If you'd like to contribute to EZGmail, check out https://github.com/asweigart/ezgmail or email al@inventwithpython.com

