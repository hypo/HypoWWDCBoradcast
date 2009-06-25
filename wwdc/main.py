#!/usr/bin/env python
#
# hypoWWDCBroadcast app v0.1
#
#   - This is the same app that used to host WWDC Keynote broadcast,
#     now we release it under new-BSD License. Hope you can benefit from it. :)
#
#   Authors: Chien-An "itsZero" Cho (Main broadcast app.)
#            Yung-Luen "yllan" Lan (Chat app.)
#
# Copyright (c) 2009, Bigs Labs.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY Bigs Labs. ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <copyright holder> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

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

# Models

class Updates(db.Model):
    """Updates model stores news updates"""
    mid = db.IntegerProperty()
    time = db.DateTimeProperty(auto_now_add=True)
    message = db.StringProperty(required=True)
    
    """Convert single update into json format"""
    def to_json(self):
        return json.dumps({'id': self.mid, 'time': (self.time + timedelta(hours=-7)).strftime('%H:%M:%S'), 'message': self.message})

class Chats(db.Model):
    """Chats model stores chatroom logs"""
    cid = db.IntegerProperty()
    time = db.DateTimeProperty(auto_now_add=True)
    nickname = db.StringProperty(required=True)
    message = db.StringProperty(required=True)

    """Convert single update into json format"""
    def to_json(self):
        return json.dumps({'id': self.cid, 'nickname': cgi.escape(self.nickname), 'message': cgi.escape(self.message)})

class MainHandler(webapp.RequestHandler):
    """This handler provide user with updates information."""
    
    def get(self):
        """ Provide user with json format news updates.
        
        User can provide a parameter called lastid to control how many data he/she need."""
        source = None
        if (self.request.get('lastid') == '0' or self.request.get('lastid') == ''):
            source = Updates.all().order('-time')
        else:
            source = Updates.all().filter('mid >', int(self.request.get('lastid'))).order('-mid')
            
        json_str = []
        for u in source:
            json_str.append(u.to_json())
            
        self.response.out.write('[' + ','.join(json_str) + ']')

class AdminHandler(webapp.RequestHandler):
    """AdminHandler provides interface with accessiable from /admin"""
    
    def get(self):
        path = os.path.join(os.path.dirname(__file__), 'admin.html')
        updates = Updates.all().order("-time")
        self.response.out.write(template.render(path, {'logout_url': users.create_logout_url("/"), 'updates': updates}))

class ResetHandler(webapp.RequestHandler):
    """You can use /admin/reset to reset all data including news and chats at once."""
    
    def get(self):
        for u in Updates.all():
            u.delete();
        for c in Chats.all():
            c.delete();
        self.redirect('/admin')

class DeleteHandler(webapp.RequestHandler):
    """Handle deleting single news update"""
    
    def get(self):
        """Delete single news update identified by parameter 'id'"""
        Updates.get(self.request.get('id')).delete()
        self.redirect('/admin')

class PostHandler(webapp.RequestHandler):
    """Post news goes to this handler."""
    
    def post(self):
        if (self.request.get('msg')):
            up = Updates(message = self.request.get('msg'))
            up.mid = Updates.all().count() + 1
            up.put()
        self.redirect('/admin')

class ChatUpdateHandler(webapp.RequestHandler):
    """Output users' chat to json format"""
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

class ChatSayHandler(webapp.RequestHandler):
    """Add users' talk to database"""
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
    application = webapp.WSGIApplication([
        ('/api/update', MainHandler),
        ('/admin', AdminHandler),
        ('/admin/post', PostHandler),
        ('/admin/reset', ResetHandler),
        ('/admin/delete', DeleteHandler),
        ('/chat/say', ChatSayHandler),
        ('/chat/update', ChatUpdateHandler),
    ], debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
