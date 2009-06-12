#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import wsgiref.handlers
import os
import cgi
from datetime import timedelta
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api import memcache

from django.utils import simplejson as json

class Chats(db.Model):
    cid = db.IntegerProperty()
    time = db.DateTimeProperty(auto_now_add=True)
    nickname = db.StringProperty(required=True)
    message = db.StringProperty(required=True)

    def to_json(self):
        return json.dumps({'id': self.cid, 'nickname': cgi.escape(self.nickname), 'message': cgi.escape(self.message)})


class MainHandler(webapp.RequestHandler):
  def get(self):
    self.response.out.write('Hello world!')


class UpdateHandler(webapp.RequestHandler):

    def get(self):
        source = None
        
        if (self.request.get('lastid') == '0' or self.request.get('lastid') == ''):
            source = Chats.all().order('-time').fetch(100)
        else:
            source = Chats.all().filter('cid >', int(self.request.get('lastid'))).order('-cid')

        json_str = []
        for u in source:
            json_str.append(u.to_json())

        self.response.out.write('[' + ','.join(json_str) + ']')

class SayHandler(webapp.RequestHandler):
    def get(self):
        if (self.request.get('msg') and self.request.get('nickname')):
            chats = []

            last_key = 0
            
            if memcache.get('lastid'):
                last_key = memcache.get('lastid')
            else:
                result = Chats.gql('ORDER BY cid').fetch(1000)
                chats.extend(result)
                if len(result) > 0:
                    last_key = result[-1].cid
                else:
                    last_key = 1

            while True:
                result = Chats.gql('WHERE cid > :1 ORDER BY cid', last_key).fetch(1000)
                chats.extend(result)
                if len(result) > 0:
                    last_key = result[-1].cid
                if len(result) < 1000:
                    break
            
            memcache.set('lastid', last_key, time=60000)

            chat = Chats(message = self.request.get('msg'), nickname = self.request.get('nickname'))
            chat.cid = last_key + 1
            chat.put()


def main():
  application = webapp.WSGIApplication([('/', MainHandler),
        ('/say', SayHandler),
        ('/update', UpdateHandler),
  ], debug=True)
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()
