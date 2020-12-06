from __future__ import division, print_function
import pytest
import ezgmail
import datetime, os, base64, shutil

# You will need to set up your own credentials.json file and token
# before you can run these tests. See the README file for instructions
# on how to do this.

# You will need to change this to match your gmail test account.
# (It's been base64 encoded so that spambot scrapers don't read it. Use
# https://www.base64encode.org/ to change the value if needed.)
TEST_EMAIL_ADDRESS = base64.b64decode('dGVzdC5zd2VpZ2FydEBnbWFpbC5jb20=').decode('utf-8') # 'test.sweigart@XXX'
TEST_SUBJECT = 'Pytest Test ' + str(datetime.datetime.now())
TXT_ATTACHMENT_FILENAME = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'attachment.txt')
JPG_ATTACHMENT_FILENAME = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'attachment.jpg')
DO_NOT_DELETE_SENDER = base64.b64decode('QWwgU3dlaWdhcnQgPGFzd2VpZ2FydEBnbWFpbC5jb20+').decode('utf-8') # 'Al Sweigart <asweigart@XXX>'

def test_init():
    # Test the basic set up with token.json and credentials.json:
    ezgmail.init()

    # Test with nonexistant token file:
    #with pytest.raises(ezgmail.EZGmailException):
    #    ezgmail.init(tokenFile='DOES_NOT_EXIST.json', credentialsFile='credentials.json')

    # Test with nonexistant credential file:
    if not os.path.exists('token-custom.json'):
        shutil.copy('token.json', 'token-custom.json')
    with pytest.raises(ezgmail.EZGmailException):
        #ezgmail.init(tokenFile='token-custom.json', credentialsFile='DOES_NOT_EXIST.json')
        ezgmail.init(credentialsFile='DOES_NOT_EXIST.json')

    # Test that exceptions aren't raised when _raiseException is False:
    #ezgmail.init(tokenFile='DOES_NOT_EXIST.json', credentialsFile='credentials.json', _raiseException=False)

    # Test the basic set up with custom names:
    if not os.path.exists('credentials-custom.json'):
        shutil.copy('credentials.json', 'credentials-custom.json')
    ezgmail.init(tokenFile='token-custom.json', credentialsFile='credentials-custom.json')

    assert ezgmail.EMAIL_ADDRESS == TEST_EMAIL_ADDRESS
    assert ezgmail.LOGGED_IN == True

def test_readEmail():
    # There should be an email with subject "DO NOT DELETE" used for the purposes of testing.
    gmailThreads = ezgmail.search('"DO NOT DELETE"')
    assert len(gmailThreads) > 0
    gmailMsg = None
    for gmailThread in gmailThreads:
        if gmailThread.messages[0].sender == 'Al Sweigart <asweigart@gmail.com>':
            gmailMsg = gmailThread.messages[0]
            break
    assert gmailMsg is not None, 'The "DO NOT DELETE" test message must have been deleted.'

    # Check this email:
    assert gmailMsg.sender == DO_NOT_DELETE_SENDER
    assert gmailMsg.subject == 'DO NOT DELETE'
    #breakpoint()
    assert gmailMsg.body == 'This is the body.\r\n'
    assert gmailMsg.recipient == TEST_EMAIL_ADDRESS
    # TODO: The following timestamp is in the central timezone.
    assert gmailMsg.timestamp == datetime.datetime(2019, 6, 23, 21, 32, 41)
    assert 'attachment.txt' in gmailMsg.attachments
    assert 'attachment.jpg' in gmailMsg.attachments

    # Delete any existing attachment downloads from previous unit test runs:
    if os.path.exists('attachment.txt'):
        os.unlink('attachment.txt')
    if os.path.exists('attachment.jpg'):
        os.unlink('attachment.jpg')

    # Download attachments:
    gmailMsg.downloadAttachment('attachment.txt')
    assert os.path.exists('attachment.txt')
    assert os.path.getsize('attachment.txt') == 53
    os.unlink('attachment.txt')

    gmailMsg.downloadAttachment('attachment.jpg')
    assert os.path.exists('attachment.jpg')
    assert os.path.getsize('attachment.jpg') == 56009
    os.unlink('attachment.jpg')

    gmailMsg.downloadAllAttachments()
    assert os.path.exists('attachment.txt')
    assert os.path.getsize('attachment.txt') == 53
    os.unlink('attachment.txt')
    assert os.path.exists('attachment.jpg')
    assert os.path.getsize('attachment.jpg') == 56009
    os.unlink('attachment.jpg')



"""
def test_basic():
    assert ezgmail.EMAIL_ADDRESS == TEST_EMAIL_ADDRESS
    assert ezgmail.LOGGED_IN == True

    attachmentFilename = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'attachment.txt')

    # This test doesn't check the results, it just makes sure these functions don't raise any exceptions:
    ezgmail.send(TEST_EMAIL_ADDRESS, TEST_SUBJECT, 'This is the body of the email.', [attachmentFilename])
    unreadThreads = ezgmail.unread()
    unreadThreads[0] # NOTE: Make sure the test email account always has at least one unread message.
    ezgmail.summary(unreadThreads, printInfo=False)
    recentThreads = ezgmail.recent()
    msg = recentThreads[0].messages[0]
    msg.sender
    msg.recipient
    msg.subject
    msg.body
    msg.timestamp
    ezgmail.search('mancala')
"""

if __name__ == '__main__':
    pytest.main()


