from __future__ import division, print_function
import pytest
import ezgmail
import datetime, os

# You will need to set up your own credentials.json file and token
# before you can run these tests. See the README file for instructions
# on how to do this.

# You will need to change this to match your gmail test account.
TEST_EMAIL_ADDRESS = 'test.sweigart@gmail.com'
TEST_SUBJECT = 'Pytest Test ' + str(datetime.datetime.now())

def test_basic():
    assert ezgmail.EMAIL_ADDRESS == TEST_EMAIL_ADDRESS

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


if __name__ == '__main__':
    pytest.main()
