from datetime import timedelta, datetime

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test.testcases import TestCase
from django.conf import settings

from entree.enauth.mailer import IdentityMailer
from entree.enauth.models import Identity, MAIL_TOKEN, LoginToken

from mock import patch
from nose.tools import assert_raises, assert_equals, assert_not_equals, assert_almost_equals


class TestMailer(TestCase):


    def setUp(self):
        super(TestMailer, self).setUp()
        cache.clear()

        self.user = Identity.objects.create(email='foo@bar.cz')

        self.mailer = IdentityMailer(self.user)


    def test_dont_send_already_activated_mail(self):
        self.user.mail_verified = True
        self.user.save()

        assert_raises(ValidationError, self.mailer.send_activation)

    def test_send_before_cooldown(self):
        self.mailer.send_activation()

        assert_raises(ValidationError, self.mailer.send_activation)

    def test_token_autocreate_on_send(self):
        assert_equals(True, self.mailer.send_activation())

    def test_moar_tokens_exists_but_handled(self):
        t1 = self.user.create_token(token_type=MAIL_TOKEN)
        t2 = self.user.create_token(token_type=MAIL_TOKEN)

        t1.touched = datetime.now() - timedelta(days=1, minutes=2)
        t1.save()

        t2.touched = datetime.now() - timedelta(days=1, minutes=1)
        t2.save()

        token_left = self.user.create_token(token_type=MAIL_TOKEN)
        token_left.touched = datetime.now() - timedelta(days=1)
        token_left.save()

        assert_equals(True, self.mailer.send_activation())
        assert_equals(1, LoginToken.objects.count())
        assert_equals(token_left.pk, LoginToken.objects.all()[0].pk)

    def test_send_more_mails_cooldown_raises(self):
        assert_equals(True, self.mailer.send_activation())
        assert_raises(ValidationError, self.mailer.send_activation)

    @patch.object(settings, 'DEBUG', True)
    def test_send_more_mails_cooldown_with_debug_pass(self):
        assert_equals(True, self.mailer.send_activation())
        assert_equals(True, self.mailer.send_activation())


    @patch('entree.enauth.mailer.send_mail')
    def test_mail_failed_token_timestamp_not_updated(self, mocked_send_mail):
        mocked_send_mail.side_effect = Exception('x')

        token_str = 'TOKENVAL'
        day_ago = datetime.now() - timedelta(days=1)
        original_token = LoginToken.objects.create(token_type=MAIL_TOKEN, touched=day_ago, value=token_str, user=self.user)

        assert_equals(False, self.mailer.send_activation())

        updated_token = LoginToken.objects.get(value=token_str)
        assert_equals(updated_token.touched, original_token.touched)

    @patch('entree.enauth.mailer.send_mail')
    def test_mail_token_timestamp_updated(self, mocked_send_mail):
        mocked_send_mail.return_value = True

        day_ago = datetime.now() - timedelta(days=1)
        original_token = LoginToken.objects.create(token_type=MAIL_TOKEN, touched=day_ago, value='fo', user=self.user)

        assert_equals(True, self.mailer.send_activation())

        updated_token = LoginToken.objects.get(pk=original_token.pk)
        assert_equals(True, (datetime.now() - updated_token.touched) < timedelta(seconds=10))


    def test_pwd_reset_token_autocreated(self):

        self.mailer.send_pwd_reset_verify()
