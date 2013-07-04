import simplejson as json

from django.http import HttpResponse


class JSONResponseMixin(object):
    def render_to_response(self, context):
        return self.get_json_response(json.dumps(context))

    def get_json_response(self, content, **httpresponse_kwargs):
        return HttpResponse(content, content_type='application/json', **httpresponse_kwargs)
