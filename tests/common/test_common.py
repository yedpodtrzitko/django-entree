from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
import simplejson as json
from hashlib import sha1

from django.test.testcases import TestCase
from django.conf import settings

from entree.common.utils import calc_checksum
from entree.common.views import JSONResponseMixin
from entree.common.context_processors import common as common_cp

from nose.tools import assert_raises, assert_equals


ENTREE = settings.ENTREE



class TestCommonStuff(TestCase):

    def test_token_checksum(self):
        token = 'foo'
        salt = 'bar'
        res = calc_checksum(token, salt)

        assert_equals(res, sha1(token + salt).hexdigest().upper())

    def test_json_response_mixin(self):

        data = {'foo': 'bar'}

        mixin = JSONResponseMixin()
        response = mixin.render_to_response(data)

        semtam_data = json.loads(response.content)

        assert_equals(semtam_data, data)

    def test_context_processor(self):
        request = HttpRequest()
        request.entree_user = AnonymousUser()
        assert_equals(dict, type(common_cp(request)))
