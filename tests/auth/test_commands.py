import os

from django.core.cache import cache
from django.core.management import call_command, CommandError
from django.test.testcases import TestCase

from entree.enauth.models import Identity

from mock import patch, Mock
from nose.tools import assert_raises, assert_equals


EMAIL = 'foo@bar.cz'
PASS = 'foo'
DEVNULL = open(os.devnull, 'w')

class MockedRaw(object):

    def __init__(self, *args, **kwargs):
        self.called = 0
        self.returns = []

    def __call__(self, prompt=""):
        prompt = prompt.lower()
        self.called += 1
        if 'mail' in prompt:
            return EMAIL
        else:
            return PASS

class MockedRawVariable(MockedRaw):

    def __call__(self, prompt=""):
        ret = self.returns[self.called]
        self.called += 1
        return ret


class TestCommands(TestCase):

    def setUp(self):
        super(TestCommands, self).setUp()
        cache.clear()


    @patch('__builtin__.raw_input', new_callable=MockedRaw)
    @patch('getpass.getpass', new_callable=MockedRaw)
    def test_create_identity(self, mocked_pass, mocked_input):
        call_command('createidentity')

        new_id = Identity.objects.get(email=EMAIL)
        assert_equals(new_id.check_password(PASS), True)

    @patch('__builtin__.raw_input')
    @patch('getpass.getpass', new_callable=MockedRaw)
    def test_create_idenity_noinput(self, mocked_pass, mocked_input):
        call_command('createidentity', email=EMAIL)

        assert_equals(mocked_input.called, False)

        new_id = Identity.objects.get(email=EMAIL)
        assert_equals(new_id.check_password(PASS), True)

    def test_create_identity_passive_without_email_raises(self):
        assert_raises(CommandError, lambda: call_command('createidentity', interactive=False, stderr=DEVNULL))

    def test_create_idenity_passive_invalid_email_raises(self):
        assert_raises(CommandError, lambda: call_command('createidentity', interactive=False, email=2*EMAIL, stderr=DEVNULL))

    @patch('__builtin__.raw_input', new_callable=MockedRaw)
    @patch('getpass.getpass', new_callable=MockedRawVariable)
    def test_create_idenity_invalid_mail_gives_prompt(self, mocked_pass, mocked_input):
        mocked_pass.returns = ['foo', 'foo']
        call_command('createidentity', email=2*EMAIL, stderr=DEVNULL)
        assert_equals(mocked_input.called, 1)

    @patch('getpass.getpass', new_callable=MockedRawVariable)
    def test_create_idenity_unmatching_pwd_repeats(self, mocked_pass):
        mocked_pass.returns = ['foo', 'bar', 'foo', 'foo']
        call_command('createidentity', interactive=True, email=EMAIL, stderr=DEVNULL)
        assert_equals(mocked_pass.called, 4)

    @patch('getpass.getpass', new_callable=MockedRawVariable)
    def test_create_idenity_empty_pwd_repeats(self, mocked_pass):
        mocked_pass.returns = ['', '', 'foo', 'foo']
        call_command('createidentity', interactive=True, email=EMAIL, stderr=DEVNULL)
        assert_equals(mocked_pass.called, 4)

    @patch('__builtin__.raw_input')
    def test_create_idenity_keybord_interrupt_works(self, mocked_input):
        mocked_input.side_effect = KeyboardInterrupt("STOP! Hammer time!")
        assert_raises(SystemExit, lambda: call_command('createidentity', stderr=DEVNULL))
