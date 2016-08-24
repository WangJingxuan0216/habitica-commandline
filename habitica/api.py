#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Phil Adams http://philadams.net

Python wrapper around the Habitica (http://habitica.com) API
http://github.com/philadams/habitica
"""


import json

import requests

API_URI_BASE = 'api/v3'
API_CONTENT_TYPE = 'application/json'


class Habitica(object):
    """
    A minimalist Habitica API class.
    """

    def __init__(self, auth=None, resource=None, aspect=None, subaspect=None):
        self.auth = auth
        self.resource = resource
        self.aspect = aspect
        self.subaspect = subaspect
        self.headers = auth if auth else {}
        self.headers.update({'content-type': API_CONTENT_TYPE})

    def __getattr__(self, m):
        try:
            return object.__getattr__(self, m)
        except AttributeError:
            if not self.resource:
                return Habitica(auth=self.auth, resource=m)

            else:
                if not self.aspect:
                    return Habitica(auth=self.auth, resource=self.resource,
                                aspect=m)
                else:
                    return Habitica(auth=self.auth, resource=self.resource,
                     aspect=self.aspect, subaspect=m)

    def __call__(self, **kwargs):
        method = kwargs.pop('_method', 'get')
        
        # build up URL... Habitica's api is the *teeniest* bit annoying
        # so either i need to find a cleaner way here, or i should
        # get involved in the API itself and... help it.
        if self.aspect:
            aspect_id = kwargs.pop('_id', None)
            subitem_id = kwargs.pop('_cid', None)
            direction = kwargs.pop('_direction', None)
            inventory1 = kwargs.pop('_inventory1', None)
            inventory2 = kwargs.pop('_inventory2', None)
            if aspect_id is not None:
                uri = '%s/%s/%s/%s/%s' % (self.auth['url'],
                                          API_URI_BASE,
                                          self.resource,
                                          str(aspect_id),
                                          self.aspect)
                if subitem_id is not None:
                    uri = '%s/%s/%s' % (uri,str(subitem_id),self.subaspect)
            else:
                uri = '%s/%s/%s/%s' % (self.auth['url'],
                                       API_URI_BASE,
                                       self.resource,
                                       self.aspect)
                if inventory1 is not None and inventory2 is not None:
                  uri = '%s/%s/%s' % (uri, inventory1, inventory2) 
            if direction is not None:
                uri = '%s/%s' % (uri, direction)
        else:
            uri = '%s/%s/%s' % (self.auth['url'],
                                API_URI_BASE,
                                self.resource)
        
        # actually make the request of the API
        if method in ['put', 'post']:
            res = getattr(requests, method)(uri, headers=self.headers,
                                            data=json.dumps(kwargs))
        else:
            res = getattr(requests, method)(uri, headers=self.headers,
                                            params=kwargs)

        # print(res.url)  # debug...
        if res.status_code == requests.codes.ok:
            return res.json()
        else:
            res.raise_for_status()
