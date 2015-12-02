import json

from django.test import Client


class AjaxClient(Client):

    def _get_kwargs(self, kwargs):
        kw = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        kw.update(kwargs)
        return kw

    def post(self, *args, **kwargs):
        return super(AjaxClient, self).post(*args, **self._get_kwargs(kwargs))

    def get(self, *args, **kwargs):
        return super(AjaxClient, self).get(*args, **self._get_kwargs(kwargs))

    def content(self, response):
        return json.loads(response.content.decode('utf-8'))
