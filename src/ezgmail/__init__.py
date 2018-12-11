'''EZGmail
A Pythonic interface to the Gmail API that actually works as of Dec 2018.

By Al Sweigart al@inventwithpython.com

Note: Unless you know what you're doing, also use the default 'me' value for userId parameters in this module.
'''

__version__ = '0.0.1'


import base64
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import mimetypes
import os
import datetime
import re
import copy

from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

#SCOPES = 'https://www.googleapis.com/auth/gmail.readonly' # read-only mode
SCOPES = 'https://mail.google.com/' # read-write mode
SERVICE = None
EMAIL_ADDRESS = None

class GmailThread:
    '''Represents a thread of Gmail messages. These objects are returned by the users.threads.get() API call. They contain references to a list of GmailMessage objects.'''
    def __init__(self, threadObj):
        self.threadObj = copy.deepcopy(threadObj)
        self.id = threadObj['id']
        self.snippet = threadObj['snippet']
        self.historyId = threadObj['historyId']
        self._messages = None


    @property
    def text(self):
        return [msg.body for msg in self.messages]


    @property
    def messages(self):
        """The GmailMessage objects of the emails in this thread, starting from most recent."""
        if self._messages is None:
            self._messages = []

            # The threadObj returned by the list() api doesn't include the messages list, so we need to call the get() api
            self.extendedThreadObj = SERVICE.users().threads().get(userId='me', id=self.id).execute()

            for msg in self.extendedThreadObj['messages']:
                self._messages.append(GmailMessage(msg))


        return self._messages

    def __str__(self):
        return '<GmailThread len=%r snippet=%r>' % (len(self.messages), self.snippet)


    def senders(self):
        """Returns a list of strings of the senders in this thread, from oldest to most recent."""
        senderEmails = []
        for msg in self.messages:
            if msg.sender == EMAIL_ADDRESS:
                senderEmails.append('me')
            else:
                senderEmails.append(msg.sender)
        return senderEmails


    def latestTimestamp(self):
        return self.messages[-1].timestamp



def removeQuotedParts(emailText):
    """Takes the body of an email and returns the text up to the quoted "reply" text that begins with "On Sun, Jan 1, 2018 at 12:00 PM al@inventwithpython.com wrote:" part."""
    replyPattern = re.compile(r'On (Sun|Mon|Tue|Wed|Thu|Fri|Sat), (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d+, \d\d\d\d at \d+:\d+ (AM|PM) (.*?) wrote:')

    mo = replyPattern.search(emailText)
    if mo is None:
        return emailText
    else:
        return emailText[:mo.start()]



class GmailMessage:
    '''Represents a Gmail messages. These objects are returned by the users.messages.get() API call. They contain all the header/subject/body information of a single email.

    Note that the `body` attribute contains text up to the quoted "reply" text that begins with "On Sun, Jan 1, 2018 at 12:00 PM al@inventwithpython.com wrote:" part.

    The full body is in the `originalBody` attribute.'''

    def __init__(self, messageObj):
        '''Create a GmailMessage objet. The `messageObj` is the dictionary returned by the users.messages.get() API call.'''
        self.messageObj = copy.deepcopy(messageObj) # TODO should we make a copy of this to prevent further modification? Sure.
        self.id = messageObj['id']
        self.threadId = messageObj['threadId']

        self.snippet = messageObj['snippet']
        self.historyId = messageObj['historyId']
        self.timestamp = datetime.datetime.fromtimestamp(int(messageObj['internalDate']) // 1000)

        # Find the headers for the sender, recipient, and subject
        for header in messageObj['payload']['headers']:
            if header['name'].upper() == 'FROM': # NOTE: I'm not sure if upper() is needed, but I use it in this method just in case.
                self.sender = header['value']
            if header['name'].upper() == 'TO':
                self.recipient = header['value']
            if header['name'].upper() == 'SUBJECT':
                self.subject = header['value']

            if header['name'].upper() == 'CONTENT-TYPE':
                emailEncoding = _parseContentTypeHeaderForEncoding(header['value'])


        # Find the plaintext email part, get the encoding, and use it to get the email body.
        if 'parts' in messageObj['payload'].keys():
            for part in messageObj['payload']['parts']:
                if part['mimeType'].upper() == 'TEXT/PLAIN':
                    # This is the plain text email we're looking for. Now find the encoding and the body.
                    for header in part['headers']:
                        if header['name'].upper() == 'CONTENT-TYPE':
                            emailEncoding = _parseContentTypeHeaderForEncoding(header['value'])

                    # `originalBody` has the full body of the email, while the more useful `body` only has everything up until the quoted reply part.
                    self.originalBody = base64.urlsafe_b64decode(part['body']['data']).decode(emailEncoding)
                    self.body = removeQuotedParts(self.originalBody)
        elif 'body' in messageObj['payload'].keys():
            #for header in messageObj['payload']['headers']:
            #    if header['name'].upper() == 'CONTENT-TYPE':
            #        emailEncoding = _parseContentTypeHeaderForEncoding(header['value'])
            self.originalBody = base64.urlsafe_b64decode(messageObj['payload']['body']['data']).decode(emailEncoding)
            self.body = removeQuotedParts(self.originalBody)



        # TODO - Future features include labels and attachments.

    def __str__(self):
        return '<GmailMessage from=%r to=%r timestamp=%r subject=%r snippet=%r>' % (self.sender, self.recipient, self.timestamp, self.subject, self.snippet)

    def senders(self):
        return [self.sender]

    def latestTimestamp(self):
        return self.timestamp


class EZGmailException(Exception):
    pass


def _parseContentTypeHeaderForEncoding(value):
    """Helper function called by GmailMessage:__init__()."""
    mo = re.search('charset="(.*?)"', value)
    if mo is None:
        emailEncoding = 'UTF-8' # We're going to assume UTF-8 and hope for the best. Safety not guaranteed.
    else:
        emailEncoding = mo.group(1)
    return emailEncoding


def init(userId='me', tokenFile='token.json', credentialsFile='credentials.json'):
    """This function must be called before any other function in EZGmail (and is automatically called by them anyway, so you don't have to explicitly call this yourself).

    This function populates the SERVICE global variable used in all Gmail API cals. It also populates EMAIL_ADDRESS with a string of the Gmail accont's email address. This
    account is determined by the credentials.json file, downloaded from Google, and token.json. If the token.json file hasn't been generated yet, this function will open
    the browser to a page to let the user log in to the Gmail account that this module will use.

    If you want to switch to a different Gmail account, call this function again with a different `tokenFile` and `credentialsFile` arguments.
    """
    global SERVICE, EMAIL_ADDRESS

    if not os.path.exists(credentialsFile):
        raise EZGmailException('Can\'t find credentials file at %s. You can download this file from https://developers.google.com/gmail/api/quickstart/python and clicking "Enable the Gmail API"' % (os.path.abspath(credentialsFile)))

    store = file.Storage(tokenFile)
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(credentialsFile, SCOPES)
        creds = tools.run_flow(flow, store)
    SERVICE = build('gmail', 'v1', http=creds.authorize(Http()))
    EMAIL_ADDRESS = SERVICE.users().getProfile(userId=userId).execute()['emailAddress']


def _createMessage(sender, recipient, subject, body):
    """Creates a MIMEText object and returns it as a base64 encoded string in a {'raw': b64_MIMEText_object} dictionary, suitable for use by _sendMessage() and the
    users.messages.send()."""
    message = MIMEText(body, 'plain')
    message['to'] = recipient
    message['from'] = sender
    message['subject'] = subject
    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')}


def _createMessageWithAttachments(sender, recipient, subject, body, attachments):
    """Creates a MIMEText object and returns it as a base64 encoded string in a {'raw': b64_MIMEText_object} dictionary, suitable for use by _sendMessage() and the
    users.messages.send(). File attachments can also be added to this message.

    `attachments` is a list of strings of filenames."""
    message = MIMEMultipart()
    message['to'] = recipient
    message['from'] = sender
    message['subject'] = subject

    messageMimeTextPart = MIMEText(body, 'plain')
    message.attach(messageMimeTextPart)

    if isinstance(attachments, str):
        attachments = [attachments] # If it's a string, put `attachments` in a list.


    for attachment in attachments:
        # Check that the file exists.
        if not os.path.exists(attachment):
            raise EZGmailException('%r passed for attachment but %s does not exist.' % (attachment, os.path.abspath(attachment)))

        content_type, encoding = mimetypes.guess_type(attachment)

        if content_type is None or encoding is not None:
            content_type = 'application/octet-stream'
        main_type, sub_type = content_type.split('/', 1)

        if main_type == 'text':
            fp = open(attachment, 'r')
            mimePart = MIMEText(fp.read(), _subtype=sub_type)
        else:
            fp = open(attachment, 'rb')
            if main_type == 'image':
              mimePart = MIMEImage(fp.read(), _subtype=sub_type)
            elif main_type == 'audio':
              mimePart = MIMEAudio(fp.read(), _subtype=sub_type)
            else:
              mimePart = MIMEBase(main_type, sub_type)
              mimePart.set_payload(fp.read())
        fp.close()

        filename = os.path.basename(attachment)
        mimePart.add_header('Content-Disposition', 'attachment', filename=filename)
        message.attach(mimePart)

    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')}


def _sendMessage(message, userId='me'):
    """Sends an email based on the `message` object, which is returned by _createMessage() or _createMessageWithAttachments()."""
    message = (SERVICE.users().messages().send(userId=userId, body=message).execute())
    return message


def send(recipient, subject, body, attachments=None, sender=None):
    """Sends an email from the configured Gmail account."""
    if SERVICE is None: init()

    if sender is None:
        sender = EMAIL_ADDRESS

    if attachments is None:
        msg = _createMessage(sender, recipient, subject, body)
    else:
        msg = _createMessageWithAttachments(sender, recipient, subject, body, attachments)
    _sendMessage(msg)


def search(query, maxResults=25, userId='me'):
    """Returns a list of GmailThread objects that match the search query.

    The `query` string is exactly the same as you would type in the Gmail search box, and you can use the search operatives for it too:

        label:UNREAD
        from:al@inventwithpython.com
        subject:hello
        has:attachment

    More are described at https://support.google.com/mail/answer/7190?hl=en
    """
    if SERVICE is None: init()

    response = SERVICE.users().threads().list(userId=userId, q=query, maxResults=maxResults).execute()
    gmailThreads = []
    if 'threads' in response:
        gmailThreads.extend(response['threads'])

    """
    while 'nextPageToken' in response:
      page_token = response['nextPageToken']
      response = SERVICE.users().threads().list(userId=userId, q=query
                                        pageToken=page_token).execute()
      gmailThreads.extend(response['threads'])
    """
    return [GmailThread(threadObj) for threadObj in gmailThreads]

'''
def searchMessages(query, maxResults=25, userId='me'):
    """Same as search(), except it returns a list of GmailMessage objects instead of GmailThread. You probably want to use search() instea dof this function."""
    if SERVICE is None: init()

    response = SERVICE.users().messages().list(userId=userId, q=query, maxResults=maxResults).execute()
    messages = []
    if 'messages' in response:
      messages.extend(response['messages'])

    """
    while 'nextPageToken' in response:
      page_token = response['nextPageToken']
      response = SERVICE.users().messages().list(userId=userId, q=query,
                                         pageToken=page_token).execute()
      messages.extend(response['messages'])
    """

    return [GmailMessage(SERVICE.users().messages().get(userId=userId, id=message['id']).execute()) for message in messages]


def getMessage(query, userId='me'):
    """Return a GmailMessage object of the first search result for `query`. Essentially a wrapper for search()."""
    if SERVICE is None: init()

    messages = searchMessages(query, 1, userId)
    if messages == []:
        raise Exception('No message matching that query found.')
    else:
        return messages[0]
'''


def recent(maxResults=25, userId='me'):
    """Return a list of GmailThread objects for the most recent emails. Essentially a wrapper for search().

    First index is the most recent."""
    return search('label:INBOX', maxResults, userId)


def unread(maxResults=25, userId='me'):
    """Return a list of GmailThread objects for unread emails. Essentially a wrapper for search()."""
    return search('label:UNREAD', maxResults, userId)


def summary(gmailObjects, printInfo=True):
    """Prints out a summary of the GmailThread or GmailMessage in the `gmailObjects` list, similar to the way """
    if isinstance(gmailObjects, (GmailThread, GmailMessage)):
        gmailObjects = [gmailObjects] # Make this uniformly in a list.

    summaryText = []
    for obj in gmailObjects:
        summaryText.append((obj.senders(), obj.snippet, obj.latestTimestamp())) # GmailThread and GmailMessage both have senders() and latestTimestamp() methods.

    if printInfo:
        summaryText = [(', '.join([name[:name.find(' ')] for name in itemSenders]), # Just use the "Al" part of "Al Sweigart <al@inventwithpython.com>"
                        itemSnippet,
                        itemLatestTimestamp.strftime('%b %d')) for itemSenders, itemSnippet, itemLatestTimestamp in summaryText]
        print('\n'.join(['%s - %s - %s' % text for text in summaryText]))
    else:
        return summaryText # Return the raw list of tuples info.