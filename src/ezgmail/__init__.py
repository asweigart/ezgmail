"""EZGmail - A Pythonic interface to the Gmail API."""

# By Al Sweigart al@inventwithpython.com
# Note: Unless you know what you're doing, also use the default 'me' value for userId parameters in this module.


__version__ = "2020.10.10"

"""
NOTES FOR DEVELOPERS AND CONTRIBUTORS:
I created this because the Gmail API and its documentation is less than ideal.
EZGmail isn't meant to be comprehensive and do everything the Gmail API lets
you do, it's meant to make the simple things simple: sending emails, checking
emails, sending and downloading file attachments, etc. The ezgmail API needs
to be dead simple, even at the expense of runtime efficiency. Error messages
should be verbose and mention probable cause; they aren't just inscrutable
phrases to look up on Stackoverflow.

Users can only be logged in as a single user at a time. This is by design to
keep things simple. If you need to handle multiple logged in accounts,
you should probably use the Gmail API directly.

Users need a credentials.json file (downloadable from TODO), then call
ezgmail.init(), which causes the gmail api


"""


import base64
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
import mimetypes
import os
import datetime
import re
import copy
import warnings

from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

# Copied from https://emailregex.com/:
EMAIL_ADDRESS_REGEX = re.compile(r'''(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])''')

# SCOPES = 'https://www.googleapis.com/auth/gmail.readonly' # read-only mode
SCOPES = "https://mail.google.com/"  # read-write mode
SERVICE_GMAIL = None
EMAIL_ADDRESS = False  # False if not logged in, otherwise the string of the email address of the logged in user.
LOGGED_IN = False  # False if not logged in, otherwise True


class EZGmailException(Exception):
    """The base class for all EZGmail-specific problems. If the ``ezgmail`` module raises something that isn't this or
    a subclass of this exception, you can assume it is caused by a bug in EZGmail."""
    pass


class EZGmailValueError(EZGmailException):
    """The EZGmail module equivalent of ValueError. This exception is raised when a parameter of an incorrect value
    (but not necessarily an incorrect type) is passed to an EZGmail function."""
    pass


class EZGmailTypeError(EZGmailException):
    """The EZGmail module equivalent of ValueError. This exception is raised when a parameter of an incorrect type
    is passed to an EZGmail function."""
    pass


class GmailThread:
    """Represents a thread of Gmail messages. These objects are returned by the users.threads.get() API call. They
    contain references to a list of GmailMessage objects."""

    def __init__(self, threadObj):
        self.threadObj = copy.deepcopy(threadObj)
        self.id = threadObj["id"]
        self.snippet = threadObj["snippet"]
        self.historyId = threadObj["historyId"]
        self._messages = None

    @property
    def text(self):
        """A list of strings, where each string is the message of a single email in this thread of emails, starting
        from the oldest at index 0 to the most recent."""
        return [msg.body for msg in self.messages]

    @property
    def messages(self):
        """The GmailMessage objects of the emails in this thread, starting from the oldest at index 0 to the most
        recent."""
        if self._messages is None:
            self._messages = []

            # The threadObj returned by the list() api doesn't include the messages list, so we need to call the get() api
            self.extendedThreadObj = SERVICE_GMAIL.users().threads().get(userId="me", id=self.id).execute()

            for msg in self.extendedThreadObj["messages"]:
                self._messages.append(GmailMessage(msg))

        # Quick sanity check to make sure it's never possible to have a GmailThread object with zero messages:
        assert len(self._messages) > 0, "GmailThread object has zero messages; please file a new bug report issue: https://github.com/asweigart/ezgmail/issues"

        return self._messages  # TODO - Return copy.deepcopy(self._messages)? Would that be safer?

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "<GmailThread numMessages=%r snippet=%r>" % (len(self.messages), self.snippet)

    def senders(self):
        """Returns a list of strings of the senders in this thread, from the oldest at index 0 to the most recent."""
        senderEmails = []
        for msg in self.messages:
            if msg.sender == EMAIL_ADDRESS:
                senderEmails.append("me")
            else:
                senderEmails.append(msg.sender)
        return senderEmails

    def latestTimestamp(self):
        """The """
        return self.messages[-1].timestamp

    def addLabel(self, label):
        """Add the label ``label`` to every message in this thread."""
        _addLabel(self, label)  # The global _addLabel() function implements this feature.

    def removeLabel(self, label):
        """Remove the label ``label`` from every message in this thread, if it's there."""
        _removeLabel(self, label)  # The global _removeLabel() function implements this feature.

    def markAsRead(self):
        """Mark every message in this thread as read. (This does the same thing as removing the UNREAD label from the
        messages.)"""
        _markAsRead(self)  # The global _markAsRead() function implements this feature.

    def markAsUnread(self):
        """Mark every message in this thread as unread. (This does the same thing as adding the UNREAD label to the
        messages.)"""
        _markAsUnread(self)  # The global _markAsUnread() function implements this feature.

    def trash(self):
        """Move every message in this thread to the Trash folder. It will be automatically removed in 30 days."""
        _trash(self)  # The global _trash() function implements this feature.

    # NOTE: Let's see if there's any demand for replying to threads instead of particular messages before adding these methods:
    #def reply(self, body, attachments=None, cc=None, bcc=None, mimeSubtype="plain"):
    #    """Like the send() function, but replies to the last message in this thread."""
    #
    #    # NOTE: Since the ``sender`` argument is ignored by Gmail anyway, I'm not including in this method the
    #    # way it is included in ``send()``.
    #    self.messages[-1].reply(body, attachments=attachments, cc=cc, bcc=bcc, mimeSubtype=mimeSubtype)
    #
    #def replyAll(self, body, attachments=None, cc=None, bcc=None, mimeSubtype="plain"):
    #    """Like the send() function, but replies to the last message in this thread."""
    #
    #    # NOTE: Since the ``sender`` argument is ignored by Gmail anyway, I'm not including in this method the
    #    # way it is included in ``send()``.
    #    self.messages[-1].replyAll(body, attachments=attachments, cc=cc, bcc=bcc, mimeSubtype=mimeSubtype)


def removeQuotedParts(emailText):
    """Returns the text in ``emailText`` up to the quoted "reply" text that begins with
    "On Sun, Jan 1, 2018 at 12:00 PM al@inventwithpython.com wrote:" part."""
    replyPattern = re.compile(
        r"On (Sun|Mon|Tue|Wed|Thu|Fri|Sat), (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d+, \d\d\d\d at \d+:\d+ (AM|PM) (.*?) wrote:"
    )

    mo = replyPattern.search(emailText)
    if mo is None:
        return emailText
    else:
        return emailText[: mo.start()]


class GmailMessage:
    """Represents a Gmail messages. These objects are returned by the users.messages.get() API call. They contain all the header/subject/body information of a single email.

    The ``sender`` attribute has a string like ``'Google <no-reply@accounts.google.com>'``.

    The ``recipient`` attribute has a string like ``al@inventwithpython.com'``.

    The ``subject`` attribute contains a string of the subject line.

    The ``body`` attribute contains text up to the quoted "reply" text that begins with
    "On Sun, Jan 1, 2018 at 12:00 PM al@inventwithpython.com wrote:" part.

    The ``originalBody`` attribute contains the full message body.

    The ``timestamp`` attribute contains a ``datetime.datetime`` object of the internal message creation timestamp (epoch
    ms), which determines ordering in the inbox.

    The ``snippet`` attribute contains a string of up to the first 200 characters of the body.

    These attributes are based on the Gmail API: https://developers.google.com/gmail/api/v1/reference/users/messages
    """

    def __init__(self, messageObj):
        """Create a GmailMessage object. The ``messageObj`` is the dictionary returned by the ``users.messages.get()`` API
        call."""
        self.messageObj = copy.deepcopy(
            messageObj
        )  # TODO should we make a copy of this to prevent further modification? Sure.
        self.id = messageObj["id"]
        self.threadId = messageObj["threadId"]
        self.body = None

        self.snippet = messageObj["snippet"]
        self.historyId = messageObj["historyId"]
        self.timestamp = datetime.datetime.fromtimestamp(int(messageObj["internalDate"]) // 1000)
        self.attachments = (
            []
        )  # Filenames of the attachments (can include duplicates). This exists so the user can know what attachments exist. Can include duplicate filenames.
        self._attachmentsInfo = (
            []
        )  # List of dictionaries: {'filename': filename as str, id': attachment id as str, 'size': size in bytes as int}. This exists because there can be multiple attachments with the same filename.

        # Find the headers for the sender, recipient, and subject
        for header in messageObj["payload"]["headers"]:
            if (
                header["name"].upper() == "FROM"
            ):  # NOTE: I'm not sure if upper() is needed, but I use it in this method just in case.
                self.sender = header["value"]
            if header["name"].upper() == "TO":
                self.recipient = header["value"]
            if header["name"].upper() == "SUBJECT":
                self.subject = header["value"]

            if header["name"].upper() == "CONTENT-TYPE":
                emailEncoding = _parseContentTypeHeaderForEncoding(header["value"])

        # Find the plaintext email part, get the encoding, and use it to get the email body.
        if "parts" in messageObj["payload"].keys():
            for part in messageObj["payload"]["parts"]:
                if part["mimeType"].upper() == "TEXT/PLAIN" and "data" in part["body"]:
                    # The plain text email will have a part['body']['data'], while attachments
                    # lack this key and instead have part['body']['attachmentId'].

                    # This is the plain text email we're looking for. Now find the encoding and the body.
                    for header in part["headers"]:
                        if header["name"].upper() == "CONTENT-TYPE":
                            emailEncoding = _parseContentTypeHeaderForEncoding(header["value"])

                    # ``originalBody`` has the full body of the email, while the more useful ``body`` only has everything up until the quoted reply part.
                    self.originalBody = base64.urlsafe_b64decode(part["body"]["data"]).decode(emailEncoding)
                    self.body = removeQuotedParts(self.originalBody)

                if part["mimeType"].upper() == "MULTIPART/ALTERNATIVE":
                    # Emails with attachments can have the body of the email in a 'multipart/alternative' area of the dictionary.
                    # There is a recursive-looking structure here, where ``part`` has it's own 'parts' list.
                    for multipartPart in part["parts"]:
                        if multipartPart["mimeType"].upper() == "TEXT/PLAIN" and "data" in multipartPart["body"]:
                            # Find the encoding and the body.
                            for header in multipartPart["headers"]:
                                if header["name"].upper() == "CONTENT-TYPE":
                                    emailEncoding = _parseContentTypeHeaderForEncoding(header["value"])

                            # ``originalBody`` has the full body of the email, while the more useful ``body`` only has everything up until the quoted reply part.
                            self.originalBody = base64.urlsafe_b64decode(multipartPart["body"]["data"]).decode(
                                emailEncoding
                            )
                            self.body = removeQuotedParts(self.originalBody)

                if "filename" in part.keys() and part["filename"] != "":
                    # This only gets the attachment ID. The actual attachment must be downloaded with downloadAttachment().
                    attachmentId = part["body"]["attachmentId"]
                    attachmentSize = part["body"]["size"]
                    self.attachments.append(part["filename"])
                    self._attachmentsInfo.append(
                        {"filename": part["filename"], "id": attachmentId, "size": attachmentSize}
                    )
        elif "body" in messageObj["payload"].keys():
            # for header in messageObj['payload']['headers']:
            #    if header['name'].upper() == 'CONTENT-TYPE':
            #        emailEncoding = _parseContentTypeHeaderForEncoding(header['value'])
            self.originalBody = base64.urlsafe_b64decode(messageObj["payload"]["body"]["data"]).decode(emailEncoding)
            self.body = removeQuotedParts(self.originalBody)

        # assert self.body is not None # Note: There's still a chance that body could have not been set.
        # TODO: what if there's only an HTML email and not plain text email?

        # TODO - Future features include labels.

    def __repr__(self):
        return "<GmailMessage from=%r to=%r timestamp=%r subject=%r snippet=%r>" % (
            self.sender,
            self.recipient,
            self.timestamp,
            self.subject,
            self.snippet,
        )

    def __str__(self):
        return self.__repr__()

    def senders(self):
        # TODO - There's only going to be one sender, but this is here because the summary() function calls senders()
        # on both thread and message objects. This isn't intended to be called by users directly.
        return [self.sender]

    def latestTimestamp(self):
        # TODO - There's only going to be one timestamp, but this is here because the summary() function calls
        # latestTimestamp() on both thread and message objects. This isn't intended to be called by users directly.
        return self.timestamp

    def downloadAttachment(self, filename, downloadFolder=".", duplicateIndex=0):
        """Download the file attachment in this message with the name ``filename`` to the local folder ``downloadFolder``.
        If there are multiple attachments with the same name, ``duplicateIndex`` needs to be passed to specify
        which attachment to download."""
        if filename not in self.attachments:
            raise EZGmailException("No attachment named %s found among %s" % (filename, list(self.attachments.keys())))

        try:
            attachmentIndex = [i for i, v in enumerate(self.attachments) if v == filename][
                duplicateIndex
            ]  # Find the duplicateIndex-th entry with this filename in self.attachments.
        except:
            raise EZGmailException(
                "There is no attachment named %s with duplicate index %s." % (filename, duplicateIndex)
            )

        attachmentObj = (
            SERVICE_GMAIL.users()
            .messages()
            .attachments()
            .get(id=self._attachmentsInfo[attachmentIndex]["id"], messageId=self.id, userId="me")
            .execute()
        )

        attachmentData = base64.urlsafe_b64decode(
            attachmentObj["data"]
        )  # TODO figure out if UTF-8 is always the best encoding to pick here.

        # If downloadFolder is specified, make sure it exists and doesn't have a file by that name.
        if not os.path.exists(downloadFolder):
            os.makedirs(downloadFolder)
        elif os.path.isfile(downloadFolder):
            raise EZGmailException("%s is a file, not a folder" % downloadFolder)

        fo = open(os.path.join(downloadFolder, filename), "wb")
        fo.write(attachmentData)
        fo.close()

    def downloadAllAttachments(self, downloadFolder=".", overwrite=True):
        """Download all of the attachments in this message to the local folder ``downloadFolder``. If ``overwrite`` is
        ``True``, existing local files will be overwritten by attachments with the same filename."""
        if not overwrite:
            attachmentFilenames = [a["filename"] for a in self._attachmentsInfo]
            if len(attachmentFilenames) != len(set(attachmentFilenames)):
                raise EZGmailException(
                    "There are duplicate filenames in this message's attachments. Pass overwrite=True to downloadAllAttachments() to download them anyway."
                )

        downloadedAttachmentFilenames = []

        # If downloadFolder is specified, make sure it exists and doesn't have a file by that name.
        if not os.path.exists(downloadFolder):
            os.makedirs(downloadFolder)
        elif os.path.isfile(downloadFolder):
            raise EZGmailException("%s is a file, not a folder" % downloadFolder)

        for attachmentInfo in self._attachmentsInfo:
            attachmentObj = (
                SERVICE_GMAIL.users()
                .messages()
                .attachments()
                .get(id=attachmentInfo["id"], messageId=self.id, userId="me")
                .execute()
            )

            attachmentData = base64.urlsafe_b64decode(
                attachmentObj["data"]
            )  # TODO figure out if UTF-8 is always the best encoding to pick here.

            downloadFilename = attachmentInfo[
                "filename"
            ]  # TODO - in a future version, we can use different names to handle attachments with duplicate filenames.

            fo = open(os.path.join(downloadFolder, downloadFilename), "wb")
            fo.write(attachmentData)
            fo.close()

            downloadedAttachmentFilenames.append(downloadFilename)
        return downloadedAttachmentFilenames

    def addLabel(self, label):
        """Add the label ``label`` to every message in this thread."""
        _addLabel(self, label)  # The global _addLabel() function implements this feature.

    def removeLabel(self, label):
        """Remove the label ``label`` from every message in this thread, if it's there."""
        _removeLabel(self, label)  # The global _removeLabel() function implements this feature.

    def markAsRead(self):
        """Mark this message as read. (This does the same thing as removing the UNREAD label from the message.)"""
        _markAsRead(self)  # The global _markAsRead() function implements this feature.

    def markAsUnread(self):
        """Mark this message as unread. (This does the same thing as adding the UNREAD label to the message.)"""
        _markAsUnread(self)  # The global _markAsUnread() function implements this feature.

    def trash(self):
        """Move this message to the Trash folder. It will be automatically removed in 30 days."""
        _trash(self)  # The global _trash() function implements this feature.

    def reply(self, body, attachments=None, cc=None, bcc=None, mimeSubtype="plain"):
        """Like the send() function, but replies to the last message in this thread."""

        # NOTE: Since the ``sender`` argument is ignored by Gmail anyway, I'm not including in this method the
        # way it is included in ``send()``.

        # From https://developers.google.com/gmail/api/guides/sending
        # If you're trying to send a reply and want the email to thread, make sure that:
        #    1. The Subject headers match
        #    2. The References and In-Reply-To headers follow the RFC 2822 standard.

        send(self.sender, self.subject, body, attachments=attachments, cc=cc, bcc=bcc, mimeSubtype=mimeSubtype, _threadId=self.threadId)

    def replyAll(self, body, attachments=None, cc=None, bcc=None, mimeSubtype="plain"):
        """Like the send() function, but replies to the last message in this thread."""

        # NOTE: Since the ``sender`` argument is ignored by Gmail anyway, I'm not including in this method the
        # way it is included in ``send()``.
        pass
        # TODO - I need to remove EMAIL_ADDRESS from the first argument here:
        #send(self.sender + ', ' + self.recipient, self.subject, body, attachments=attachments, cc=cc, bcc=bcc, mimeSubtype=mimeSubtype, _threadId=self.threadId)


def _parseContentTypeHeaderForEncoding(value):
    """Helper function called by GmailMessage:__init__()."""
    mo = re.search('charset="(.*?)"', value)
    if mo is None:
        emailEncoding = "UTF-8"  # We're going to assume UTF-8 and hope for the best. "Safety not guaranteed."
    else:
        emailEncoding = mo.group(1)
    return emailEncoding


def init(userId="me", tokenFile="token.json", credentialsFile="credentials.json", _raiseException=True):
    """This function must be called before any other function in EZGmail (and is automatically called by them anyway,
    so you don't have to explicitly call this yourself).

    This function populates the ``SERVICE_GMAIL`` global variable used in all Gmail API calls. It also populates
    ``EMAIL_ADDRESS`` with a string of the Gmail account's email address (and sets the global ``LOGGED_IN`` to ``True``). This account is determined by the *credentials.json* file, downloaded from Google, and *token.json*. If the ``tokenFile``
    file hasn't been generated yet, this function will open the browser to a page to let the user log in to the Gmail account that this module will use.

    If you want to switch to a different Gmail account, call this function again with a different ``tokenFile`` and
    ``credentialsFile`` arguments.
    """
    global SERVICE_GMAIL, EMAIL_ADDRESS, LOGGED_IN

    # Set this to False, in case module was initialized before but this current initialization fails.
    EMAIL_ADDRESS = False
    LOGGED_IN = False

    try:
        if not os.path.exists(credentialsFile):
            raise EZGmailException(
                'Can\'t find credentials file at %s. You can download this file from https://developers.google.com/gmail/api/quickstart/python and clicking "Enable the Gmail API". Rename the downloaded file to credentials.json.'
                % (os.path.abspath(credentialsFile))
            )

        store = file.Storage(tokenFile)
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets(credentialsFile, SCOPES)
            creds = tools.run_flow(flow, store)
        SERVICE_GMAIL = build("gmail", "v1", http=creds.authorize(Http()))
        EMAIL_ADDRESS = SERVICE_GMAIL.users().getProfile(userId=userId).execute()["emailAddress"]
        LOGGED_IN = bool(EMAIL_ADDRESS)

        return EMAIL_ADDRESS
    except:
        if _raiseException:
            raise
        else:
            return False


def _createMessage(sender, recipient, subject, body, cc=None, bcc=None, mimeSubtype="plain", _threadId=None):
    """Creates a MIMEText object and returns it as a base64 encoded string in a ``{'raw': b64_MIMEText_object} ``
    dictionary, suitable for use by ``_sendMessage()`` and the ``users.messages.send()`` Gmail API.

    Note that the ``sender`` argument seems to be ignored by Gmail, which uses the account's actual email addresss."""
    if not isinstance(mimeSubtype, str):
        raise EZGmailTypeError('wrong type passed for mimeSubtype arg; must be "plain" or "html"')
    mimeSubtype = mimeSubtype.lower()
    if mimeSubtype not in ("html", "plain"):
        raise EZGmailValueError('wrong string passed for mimeSubtype arg; must be "plain" or "html"')

    message = MIMEText(body, mimeSubtype)
    message["to"] = recipient
    message["from"] = sender
    message["subject"] = subject
    if cc is not None:
        message["cc"] = cc
    if bcc is not None:
        message["bcc"] = bcc

    rawMessage = {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")}
    if _threadId is not None:
        rawMessage['threadId'] = _threadId
    return rawMessage


def _createMessageWithAttachments(sender, recipient, subject, body, attachments, cc=None, bcc=None, mimeSubtype="plain", _threadId=None):
    """Creates a MIMEText object and returns it as a base64 encoded string in a ``{'raw': b64_MIMEText_object}``
    dictionary, suitable for use by ``_sendMessage()`` and the ``users.messages.send()`` Gmail API. File attachments can
    also be added to this message.

    The ``sender``, ``recipient``, ``subject``, ``body`` arguments are strings.

    The ``attachments`` argument is a list of strings of filenames.

    The ``cc`` and ``bcc`` arguments are strings with comma-delimited email addresses.

    Note that the ``sender`` argument seems to be ignored by Gmail, which uses the account's actual email address.
    """
    if not isinstance(mimeSubtype, str):
        raise EZGmailTypeError('wrong type passed for mimeSubtype arg; must be "plain" or "html"')
    mimeSubtype = mimeSubtype.lower()
    if mimeSubtype not in ("html", "plain"):
        raise EZGmailValueError('wrong string passed for mimeSubtype arg; mimeSubtype arg must be "plain" or "html"')

    message = MIMEMultipart()
    message["to"] = recipient
    message["from"] = sender
    message["subject"] = subject
    if cc is not None:
        message["cc"] = cc
    if bcc is not None:
        message["bcc"] = bcc

    messageMimeTextPart = MIMEText(body, mimeSubtype)
    message.attach(messageMimeTextPart)

    if isinstance(attachments, str):
        attachments = [attachments]  # If it's a string, put ``attachments`` in a list.

    for attachment in attachments:
        # Check that the file exists.
        if not os.path.exists(attachment):
            raise EZGmailException(
                "%r passed for attachment but %s does not exist." % (attachment, os.path.abspath(attachment))
            )

        content_type, encoding = mimetypes.guess_type(attachment)

        if content_type is None or encoding is not None:
            content_type = "application/octet-stream"
        main_type, sub_type = content_type.split("/", 1)

        if main_type == "text":
            fp = open(attachment, "r")
            mimePart = MIMEText(fp.read(), _subtype=sub_type)
        else:
            fp = open(attachment, "rb")
            if main_type == "image":
                mimePart = MIMEImage(fp.read(), _subtype=sub_type)
            elif main_type == "audio":
                mimePart = MIMEAudio(fp.read(), _subtype=sub_type)
            else:
                mimePart = MIMEBase(main_type, sub_type)
                mimePart.set_payload(fp.read())
                encoders.encode_base64(mimePart)
        fp.close()

        filename = os.path.basename(attachment)
        mimePart.add_header("Content-Disposition", "attachment", filename=filename)
        message.attach(mimePart)

    rawMessage = {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")}
    if _threadId is not None:
        rawMessage['threadId'] = _threadId
    return rawMessage


def _sendMessage(message, userId="me"):
    """Sends an email based on the ``message`` object, which is returned by ``_createMessage()`` or
    ``_createMessageWithAttachments()``."""
    message = SERVICE_GMAIL.users().messages().send(userId=userId, body=message).execute()
    return message


def send(recipient, subject, body, attachments=None, sender=None, cc=None, bcc=None, mimeSubtype="plain", _threadId=None):
    """Sends an email from the configured Gmail account.

    Note that the ``sender`` argument seems to be ignored by Gmail, which uses the account's actual email address.

    TODO - Add additional details to this docstring."""
    if not isinstance(mimeSubtype, str):
        raise EZGmailTypeError('wrong type passed for mimeSubtype arg; must be "plain" or "html"')
    mimeSubtype = mimeSubtype.lower()
    if mimeSubtype not in ("html", "plain"):
        raise EZGmailValueError('wrong string passed for mimeSubtype arg; mimeSubtype arg must be "plain" or "html"')

    if SERVICE_GMAIL is None:
        init()

    if sender is None:
        sender = EMAIL_ADDRESS

    if attachments is None:
        msg = _createMessage(sender, recipient, subject, body, cc, bcc, mimeSubtype, _threadId=_threadId)
    else:
        msg = _createMessageWithAttachments(sender, recipient, subject, body, attachments, cc, bcc, mimeSubtype, _threadId=_threadId)
    _sendMessage(msg)


def search(query, maxResults=25, userId="me"):
    """Returns a list of GmailThread objects that match the search query.

    The ``query`` string is exactly the same as you would type in the Gmail search box, and you can use the search
    operatives for it too:

        * label:UNREAD
        * from:al@inventwithpython.com
        * subject:hello
        * has:attachment

    More are described at https://support.google.com/mail/answer/7190?hl=en
    """
    if SERVICE_GMAIL is None:
        init()

    response = SERVICE_GMAIL.users().threads().list(userId=userId, q=query, maxResults=maxResults).execute()
    gmailThreads = []
    if "threads" in response:
        gmailThreads.extend(response["threads"])

    """
    while 'nextPageToken' in response:
      page_token = response['nextPageToken']
      response = SERVICE_GMAIL.users().threads().list(userId=userId, q=query
                                        pageToken=page_token).execute()
      gmailThreads.extend(response['threads'])
    """
    return [GmailThread(threadObj) for threadObj in gmailThreads]


'''
def searchMessages(query, maxResults=25, userId='me'):
    """Same as search(), except it returns a list of GmailMessage objects instead of GmailThread. You probably want to use search() instea dof this function."""
    if SERVICE_GMAIL is None: init()

    response = SERVICE_GMAIL.users().messages().list(userId=userId, q=query, maxResults=maxResults).execute()
    messages = []
    if 'messages' in response:
      messages.extend(response['messages'])

    """
    while 'nextPageToken' in response:
      page_token = response['nextPageToken']
      response = SERVICE_GMAIL.users().messages().list(userId=userId, q=query,
                                         pageToken=page_token).execute()
      messages.extend(response['messages'])
    """

    return [GmailMessage(SERVICE_GMAIL.users().messages().get(userId=userId, id=message['id']).execute()) for message in messages]


def getMessage(query, userId='me'):
    """Return a GmailMessage object of the first search result for ``query``. Essentially a wrapper for search()."""
    if SERVICE_GMAIL is None: init()

    messages = searchMessages(query, 1, userId)
    if messages == []:
        raise Exception('No message matching that query found.')
    else:
        return messages[0]
'''


def recent(maxResults=25, userId="me"):
    """Return a list of ``GmailThread`` objects for the most recent emails. Essentially a wrapper for ``search()``.

    First index is the most recent."""
    return search("label:INBOX", maxResults, userId)


def unread(maxResults=25, userId="me"):
    """Return a list of ``GmailThread`` objects for unread emails. Essentially a wrapper for ``search()``."""
    return search("label:UNREAD", maxResults, userId)


def summary(gmailObjects, printInfo=True):
    """Prints out a summary of the ``GmailThread`` or ``GmailMessage`` in the ``gmailObjects`` list."""
    if SERVICE_GMAIL is None:
        init()

    if isinstance(gmailObjects, (GmailThread, GmailMessage)):
        gmailObjects = [gmailObjects]  # Make this uniformly in a list.

    summaryText = []
    for obj in gmailObjects:
        summaryText.append(
            (obj.senders(), obj.snippet, obj.latestTimestamp())
        )  # GmailThread and GmailMessage both have senders() and latestTimestamp() methods.

    if printInfo:
        summaryText = [
            (
                ", ".join(
                    [name[: name.find(" ")] for name in itemSenders]
                ),  # Just use the "Al" part of "Al Sweigart <al@inventwithpython.com>"
                itemSnippet,
                itemLatestTimestamp.strftime("%b %d"),
            )
            for itemSenders, itemSnippet, itemLatestTimestamp in summaryText
        ]
        print("\n".join(["%s - %s - %s" % text for text in summaryText]))
    else:
        return summaryText  # Return the raw list of tuples info.


def removeLabel(*args, **kwargs):
    # This deprecation warning added in version 2020.9.30:
    warnings.warn('Do not call the removeLabel() function directly, but rather the removeLabel() methods in the GmailMessage and GmailThread classes.')
    _removeLabel(*args, **kwargs)


def _removeLabel(gmailObjects, label, userId="me"):
    # This is a helper function not meant to be called directly by the user.
    if SERVICE_GMAIL is None:
        init()

    if isinstance(gmailObjects, (GmailThread, GmailMessage)):
        gmailObjects = [gmailObjects]  # Make this uniformly in a list.

    removeUnreadLabelObj = {"removeLabelIds": [label], "addLabelIds": []}
    for obj in gmailObjects:
        if isinstance(obj, GmailThread):
            SERVICE_GMAIL.users().threads().modify(userId=userId, id=obj.id, body=removeUnreadLabelObj).execute()
        elif isinstance(obj, GmailMessage):
            SERVICE_GMAIL.users().messages().modify(userId=userId, id=obj.id, body=removeUnreadLabelObj).execute()


def addLabel(*args, **kwargs):
    # This deprecation warning added in version 2020.9.30:
    warnings.warn('Do not call the addLabel() function directly, but rather the addLabel() methods in the GmailMessage and GmailThread classes.')
    _addLabel(*args, **kwargs)

def label_name_to_id(labelName):
    '''Given a string with the name of a label (i.e "TEST" or "UNREAD") it returns the ID of this label.
    :param: labelname - String with the LABEL name (i.e "UNREAD")
    Returns the string with the ID of the LABEL or it returns False in case of an error or not found.
    '''
    results = SERVICE_GMAIL.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])

    for label in labels:
        if labelName == label['name']:
            return label['id']
    return False

def _addLabel(gmailObjects, label, userId="me"):
    # This is a helper function not meant to be called directly by the user.
    if SERVICE_GMAIL is None:
        init()

    if isinstance(gmailObjects, (GmailThread, GmailMessage)):
        gmailObjects = [gmailObjects]  # Make this uniformly in a list.
        
    label = label_name_to_id(label)

    removeUnreadLabelObj = {"removeLabelIds": [], "addLabelIds": [label]}
    for obj in gmailObjects:
        if isinstance(obj, GmailThread):
            SERVICE_GMAIL.users().threads().modify(userId=userId, id=obj.id, body=removeUnreadLabelObj).execute()
        elif isinstance(obj, GmailMessage):
            SERVICE_GMAIL.users().messages().modify(userId=userId, id=obj.id, body=removeUnreadLabelObj).execute()


def markAsRead(*args, **kwargs):
    # This deprecation warning added in version 2020.9.30:
    warnings.warn('Do not call the markAsRead() function directly, but rather the markAsRead() methods in the GmailMessage and GmailThread classes.')
    _markAsRead(*args, **kwargs)


def _markAsRead(gmailObjects, userId="me"):
    # This is a helper function not meant to be called directly by the user.
    _removeLabel(gmailObjects, "UNREAD", userId)


def markAsUnread(*args, **kwargs):
    # This deprecation warning added in version 2020.9.30:
    warnings.warn('Do not call the markAsUnread() function directly, but rather the markAsUnread() methods in the GmailMessage and GmailThread classes.')
    _markAsUnread(*args, **kwargs)


def _markAsUnread(gmailObjects, userId="me"):
    # This is a helper function not meant to be called directly by the user.
    _addLabel(gmailObjects, "UNREAD", userId)


def _trash(gmailObjects, userId="me"):
    if SERVICE_GMAIL is None:
        init()

    if isinstance(gmailObjects, (GmailThread, GmailMessage)):
        gmailObjects = [gmailObjects]  # Make this uniformly in a list.

        for obj in gmailObjects:
            if isinstance(obj, GmailThread):
                SERVICE_GMAIL.users().threads().trash(userId=userId, id=obj.id).execute()
            elif isinstance(obj, GmailMessage):
                SERVICE_GMAIL.users().messages().trash(userId=userId, id=obj.id).execute()

init(_raiseException=False)
