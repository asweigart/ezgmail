# EZGmail
# By Al Sweigart al@inventwithpython.com

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


class GmailThread:
    def __init__(self, threadObj):
        self.threadObj = copy.deepcopy(threadObj)
        self.id = threadObj['id']
        self.snippet = threadObj['snippet']
        self.historyId = threadObj['historyId']
        self._messages = None

        # The threadObj returned by the list() api doesn't include the messages list, so we need to call the get() api
        self.extendedThreadObj = SERVICE.users().threads().get(userId='me', id=self.id).execute()

    @property
    def messages(self):
        if self._messages is None:
            self._messages = []

            for msg in self.extendedThreadObj['messages']:
                self._messages.append(GmailMessage(msg))


        return self._messages

    def __str__(self):
        return '<GmailThread len=%r snippet=%r>' % (len(self.messages), self.snippet)



class GmailMessage:
    def __init__(self, messageObj):
        self.messageObj = copy.deepcopy(messageObj) # TODO should we make a copy of this to prevent further modification? Sure.
        self.id = messageObj['id']
        self.threadId = messageObj['threadId']

        self.snippet = messageObj['snippet']
        self.historyId = messageObj['historyId']
        self.timestamp = datetime.datetime.fromtimestamp(int(messageObj['internalDate']) // 1000)

        # Find the headers for the sender, recipient, and subject
        for header in messageObj['payload']['headers']:
            if header['name'].upper() == 'FROM': # NOTE: I'm not sure if upper() is needed here, but I have it just in case.
                self.sender = header['value']
            if header['name'].upper() == 'TO':
                self.recipient = header['value']
            if header['name'].upper() == 'SUBJECT':
                self.subject = header['value']

        # Find the plaintext email part, get the encoding, and use it to get the email body.
        for part in messageObj['payload']['parts']:
            if part['mimeType'].upper() == 'TEXT/PLAIN':
                # This is the plain text email we're looking for.
                for header in part['headers']:
                    if header['name'].upper() == 'CONTENT-TYPE':
                        mo = re.search('charset="(.*?)"', header['value'])
                        if mo is None:
                            emailEncoding = 'UTF-8' # We're going to default to UTF-8 and hope for the best.
                        else:
                            emailEncoding = mo.group(1)
                self.body = base64.urlsafe_b64decode(part['body']['data']).decode(emailEncoding)

        # TODO - Future features include labels and attachments.

    def __str__(self):
        return '<GmailMessage from=%r to=%r timestamp=%r subject=%r snippet=%r>' % (self.sender, self.recipient, self.timestamp, self.subject, self.snippet)





def init():
    global SERVICE
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    SERVICE = build('gmail', 'v1', http=creds.authorize(Http()))


def _createMessage(sender, recipient, subject, body):
    message = MIMEText(body, 'plain')
    message['to'] = recipient
    message['from'] = sender
    message['subject'] = subject
    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')}


def _createMessageWithAttachments(sender, recipient, subject, body, attachments):
    message = MIMEMultipart()
    message['to'] = recipient
    message['from'] = sender
    message['subject'] = subject

    messageMimeTextPart = MIMEText(body, 'plain')
    message.attach(messageMimeTextPart)

    for attachment in attachments:
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


def _sendMessage(message, user_id='me'):
    message = (SERVICE.users().messages().send(userId=user_id, body=message).execute())
    return message


def _searchForEmails(query, user_id='me'):
    threads = SERVICE.users().threads().list(userId=user_id, q=query).execute().get('threads', [])
    for thread in threads:
        tdata = SERVICE.users().threads().get(userId=user_id, id=thread['id']).execute()

        print(len(tdata['messages']))
        msg = tdata['messages'][0]['payload']
        break
        subject = ''
        for header in msg['headers']:
            if header['name'] == 'Subject':
                subject = header['value']
                break
        if subject:  # skip if no Subject line
            print('- %s' % (subject))


def send(sender, recipient, subject, body, attachments=None):
    if attachments is None:
        msg = _createMessage(sender, recipient, subject, body)
    else:
        msg = _createMessageWithAttachments(sender, recipient, subject, body, attachments)
    _sendMessage(msg)


def search(query, user_id='me'):
    response = SERVICE.users().threads().list(userId=user_id, q=query).execute()
    gmailThreads = []
    if 'threads' in response:
        gmailThreads.extend(response['threads'])

    while 'nextPageToken' in response:
      page_token = response['nextPageToken']
      response = SERVICE.users().threads().list(userId=user_id, q=query,
                                        pageToken=page_token).execute()
      gmailThreads.extend(response['threads'])

    #print([t.keys() for t in gmailThreads])

    return [GmailThread(threadObj) for threadObj in gmailThreads]

