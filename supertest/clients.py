import json

from django.test import Client


class AjaxClient(Client):

    def _get_kwargs(self, kwargs, extra={}):
        kw = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        kw.update(kwargs)
        kw.update(extra)
        return kw

    def _handle_json(self, data, kwargs):
        extra = {}
        if kwargs.pop('json', False):
            data = json.dumps(data)
            extra['content_type'] = 'application/json'
        return data, extra

    def post(self, url, data=None, **kwargs):
        data, extra = self._handle_json(data, kwargs)
        return super(AjaxClient, self).post(url, data, **self._get_kwargs(kwargs, extra))

    def get(self, url, data=None, **kwargs):
        data, extra = self._handle_json(data, kwargs)
        return super(AjaxClient, self).get(url, data, **self._get_kwargs(kwargs))

    def content(self, response):
        return json.loads(response.content.decode('utf-8'))
