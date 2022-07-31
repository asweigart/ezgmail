EZGmail
======

A Pythonic interface to the Gmail API that actually works as of February 2022.

The official Gmail API quickstart doesn't actually seem to work on Python 3 without some adjustments, and the entire documentation is a bit much for someone who just wants to read and send emails from their Gmail account. I created EZGmail as a simple module that just works.

The Gmail API documentation by Google is available at https://developers.google.com/gmail/api/

Full EZGmail documentation is available at https://ezgmail.readthedocs.io/en/latest/

Installation
------------

To install with pip, run:

    pip install ezgmail

You will need to download a *credentials-gmail.json* file by going to https://developers.google.com/gmail/api/quickstart/python and clicking the **Enable the Gmail API** button (after logging in to your Gmail account). You will need to rename the downloaded *credentials-gmail.json* file to *credentials.json*.

Once you have the *credentials.json* file, the first time you run ``import ezgmail`` it will bring up a window asking you to log in to your Gmail account and allow "Quickstart" to access it. A *token.json* file will be generated which your script can use to access your account.

Future calls to ``ezgmail.init()`` or any other ``ezgmail`` function won't require this token-generating step. The ``gmail.init()`` function is automatically called when any other ``ezgmail`` function is called.


Quickstart Guide
----------------

After you've downloaded a *credentials-gmail.json* and *token-gmail.json* file, you can import EZGmail with ``import ezgmail``. To see what email address you are sending from, examine ``ezgmail.EMAIL_ADDRESS`` (this is configured by the *token-gmail.json* file you're using, and you must first call ``ezgmail.init()`` or some other ``ezgmail`` function first):

    >>> import ezgmail
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

You can also call the ``recent()`` function to get recent email threads:

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

The ``trash()`` method deletes the message or messages in a ``GmailMessage`` or ``GmailThread`` object:

    >>> import ezgmail
    >>> threads = ezgmail.search('mancala')
    >>> threads[0].trash()  # Move the entire first thread to the Trash folder.

The ``search()`` function can accept search operators just like the query text field:

* label:UNREAD
* from:al@inventwithpython.com
* subject:hello
* has:attachment

More are described at https://support.google.com/mail/answer/7190?hl=en

The ``search()``, ``recent()``, and ``unread()`` can also accept a ``maxResults`` keyword argument that is set to 25 by default. This sets an upper limit on how many threads/messages will be returned. API usage quotas are posted at https://developers.google.com/gmail/api/v1/reference/quota (roughly one million requests a day (and 25 per second) for the free tier).

By default, EZGmail sends messages as plaintext. You can send HTML emails by passing ``'html'`` for the ``mimeSubtype`` parameter in ``send()``. (By default, this parameter is set to ``'plain'``.) This email has "Hello" appear in bold and "body" appear italicized:

    >>> ezgmail.send('recipient@example.com', 'Subject Line', '<strong>Hello</strong>, this is the <em>body</em> of the message.', mimeSubtype='html')

Accessing an email or thread doesn't mark it as unread automatically. You must do that yourself by calling the ``markAsRead()`` method of the ``GmailThread`` or ``GmailMessage`` object. (There is also a corresponding ``markAsUnread()`` function.) You can also call ``ezgmail.markAsRead()`` and pass it a list of ``GmailThread`` or ``GmailMessage`` objects.

    >>> import ezgmail
    >>> unreadThreads = ezgmail.unread()
    >>> ezgmail.markAsRead(unreadThreads) # Marks all the GmailThread objects in the unreadThreads list as read.
    >>> # Or you can do:
    >>> for unreadThread in unreadThreads:
    ...     unreadThread.markAsRead() # Mark the individual GmailThread objects as read.

These two functions make add/remove the ``'UNREAD'`` label using EZGmail's ``addLabel()`` and ``removeLabel()`` functions:

    >>> import ezgmail
    >>> unreadThreads = ezgmail.unread()
    >>> ezgmail.removeLabel(unreadThreads, 'UNREAD') # Also marks threads as read.
    >>> ezgmail.addLabel(unreadThreads, 'UNREAD') # Marks them as unread again.
    >>> # Or you can do:
    >>> for unreadThread in unreadThreads:
    ...     unreadThread.removeLabel(unreadThreads, 'UNREAD') # Mark the individual GmailThread objects as read.

(Currently EZGmail doesn't have functions for adding/deleting/managing custom labels.)

To view the attachments of an email, look at the ``GmailMessage`` object's ``attachments`` dictionary. The keys are the filenames of the attachments. You can either call the ``downloadAttachment()`` or ``downloadAllAttachments()`` methods:

    >>> import ezgmail
    >>> threads = ezgmail.search('See the attached files')
    >>> threads[0].messages[0].attachments
	>>> import pprint
	>>> pprint.pprint(threads[0].messages[0].attachments)
	{'a.png': {'id': 'ANGjdJ8eLDbjBpFTfvpuQ2HfR_iwp59XLUIl-IHW8eJcexMsxBYoPCZAXcX16rnqcbJZTknF5r3GmnM1W9n4vAE1oiVgUa4S4zBmNs7rd5PzFwLjO2vU3hp3_9SEZv-KBqVxi9nuNjarxhFqp3mxw6E5mqEYmFOYtT7Gx6CZbLaJuUox9GaWu-W9B4-XPDjwKkEfCdJ21FlOl-CsC6isZgD2Vh-ghh1haZN_2sifccznLv61ZW_KmqPKFcV1j7cXMQVqWU7bkgdH8do4Msc3QsG2ly_PNRid4-7gihsXaLI1ko_j3LSvsoLHFP3edhxh6YKQ2OdMhyZh5lqjmfT1TXgSo7hY16P_ScDO5MnWvmKscf_Hm5y5D4DHfwOq4--Otivoq2WVkVucVUJBkAoB',
	           'size': 833609},
	 'b.png': {'id': 'ANGjdJ_WYMmPmy2Dd2VBgvVoLAd1p3ARxGXKIzVfKqAiLhvKSBmEowYqFCdHbMJYlDZy4IWBGLg0eQCllMI0icqamM7vfMxBW2irJVogLM6SUT9cIcJFMSF7UhzU2I26bho086J7NjnX5u4kqYj_LHchowO56vTdKLRRsaJ2gfW0esz3cDFZzvthdR4wyBKEIeCJv7OJmFiaJIRf9f1KmFfKPLo9GZSyD2RMXdd6Qa2M3uN9pgT6sZ-OQx3e6aNDAKWh5GCeSiuIt_Z7GsDCdzVJjakMJx5FRFhp5zIck0p04AHnYhKfy1BipWmf7G-DAKzgJHAhFimBVUIBeFsHrqEGxDlevD7lK4ZBeb8cluSmYyEsRkSPSMYMlp-x1GVw25gqMnMVkGMKPfwj38iB',
    	       'size': 335911}}
	>>> threads[0].messages[0].downloadAttachment('a.png') # Download to current working directory.
    >>> threads[0].messages[0].downloadAttachment('b.png', '/path/to/save/in')
    >>> threads[0].messages[0].downloadAllAttachments() # Easier way to save all attachments.


Limitations
-----------

Currently, EZGmail cannot do the following:

* Read or set labels. (Including marking emails as read.)
* Sending emails with cc and bcc fields.
* A lot of other basic features. This package is just a start!

Contribute
----------

If you'd like to contribute to EZGmail, check out https://github.com/asweigart/ezgmail or email al@inventwithpython.com


Support
-------

If you find this project helpful and would like to support its development, [consider donating to its creator on Patreon](https://www.patreon.com/AlSweigart).
