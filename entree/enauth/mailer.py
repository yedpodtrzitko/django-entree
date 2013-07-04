import logging

from base64 import b64encode
from datetime import timedelta, datetime

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.template.context import Context
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from entree.enauth.models import LoginToken, MAIL_TOKEN, MAIL_COOLDOWN, RESET_TOKEN


logger = logging.getLogger(__name__)


class IdentityMailer(object):

    def __init__(self, identity):
        self.identity = identity
        self._token = None

    @property
    def token(self):
        return self._token

    def _get_token(self, token_type):
        """
        Get or create token of requested type for given user:
        - if no token exists, create it
        - if exactly one token exists, use it
        - if more than one token exists, keep only last one (max `touched`)

        if existing token is used, check last time of send. If it is sent too \
         quick, raise ValidationError

        @param token_type: identifier of token, one value from TOKEN_TYPES
        @type token_type: str
        @return: instance of requested LoginToken
        @rtype: LoginToken
        """
        new_token = False  # `obtained token already exist` flag
        try:
            token = LoginToken.objects.get(token_type=token_type, user=self.identity)
        except LoginToken.MultipleObjectsReturned:
            tokens = LoginToken.objects.filter(token_type=token_type, user=self.identity).order_by('-touched')
            token, delete_pks = tokens[0], [one.pk for one in tokens[1:]]
            LoginToken.objects.filter(pk__in=delete_pks).delete()
        except LoginToken.DoesNotExist:
            token = self.identity.create_token(token_type=token_type)
            new_token = True

        if not new_token and (token.touched + timedelta(seconds=MAIL_COOLDOWN) > datetime.now()):
            if not settings.DEBUG:
                raise ValidationError("Email was send a few moments ago, wait for a while")
            logger.error("Mailing cooldown ignored due to active DEBUG")

        return token

    def _send_mail(self, subject, message, from_email=None):
        """
        common wrapper for django's send_mail function
        if mail is sucessfuly sent, token `touched` flag is updated

        @return: result of mail send
        @rtype: bool
        """
        recipient_list = [self.identity.email]

        try:
            send_mail(subject, message, from_email, recipient_list)
        except Exception, e:
            logger.error("Submit of mail failed", extra={
                'exception': e,
                'subject': subject,
                'recipient_list': recipient_list})
            return False
        else:
            self.token.touched = datetime.now()
            self.token.save()
            return True

    def send_activation(self):
        """
        create token for mail_activation and send instructions in email

        @return: result of email send
        @rtype: bool
        """
        if self.identity.mail_verified:
            raise ValidationError("Email is already verified")

        self._token = self._get_token(token_type=MAIL_TOKEN)

        site_domain = Site.objects.get_current().domain
        activate_link = reverse('verify_identity', kwargs={
            'email': b64encode(self.identity.email),
            'token': self.token.value
        })

        activate_url = "http://%s/%s" % (site_domain.rstrip('/'), activate_link.lstrip('/'))
        message = render_to_string("email/verify.html", context_instance=Context({
            "activate_link": activate_url,
            'site': site_domain,
        }))
        subject = _("Your account confirmation for %s" % site_domain)
        return self._send_mail(subject, message)

    def send_pwd_reset_verify(self):
        """
        create password reset token and send instructions in email

        @return: result of email send
        @rtype: bool
        """
        self._token = self._get_token(token_type=RESET_TOKEN)

        reset_link = reverse('recovery_finish', kwargs={
            'email': b64encode(self.identity.email),
            'token': self.token.value
        })

        reset_url = "http://%s/%s" % (Site.objects.get_current().domain.rstrip('/'), reset_link.lstrip('/'))
        message = render_to_string('email/reset.html', context_instance=Context({
            'reset_link': reset_url,
        }))
        subject = _("Password recovery requested")
        return self._send_mail(subject, message)
