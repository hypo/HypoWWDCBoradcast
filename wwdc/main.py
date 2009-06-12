#!/usr/bin/env python
import wsgiref.handlers
import os
from datetime import timedelta
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users
from django.utils import simplejson as json

class Updates(db.Model):
	mid = db.IntegerProperty()
	time = db.DateTimeProperty(auto_now_add=True)
	message = db.StringProperty(required=True)
	
	def to_json(self):
		return json.dumps({'id': self.mid, 'time': (self.time + timedelta(hours=-7)).strftime('%H:%M:%S'), 'message': self.message})

class MainHandler(webapp.RequestHandler):
	def get(self):
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
	def get(self):
		path = os.path.join(os.path.dirname(__file__), 'admin.html')
		updates = Updates.all().order("-time")
		self.response.out.write(template.render(path, {'logout_url': users.create_logout_url("/"), 'updates': updates}))

class ResetHandler(webapp.RequestHandler):
	def get(self):
		for u in Updates.all():
			u.delete();
		self.redirect('/admin')

class DeleteHandler(webapp.RequestHandler):
	def get(self):
		Updates.get(self.request.get('id')).delete()
		self.redirect('/admin')

class PostHandler(webapp.RequestHandler):
	def post(self):
		if (self.request.get('msg')):
			up = Updates(message = self.request.get('msg'))
			up.mid = Updates.all().count() + 1
			up.put()
		self.redirect('/admin')

def main():
	application = webapp.WSGIApplication([
		('/api/update', MainHandler),
		('/admin', AdminHandler),
		('/admin/post', PostHandler),
		('/admin/reset', ResetHandler),
		('/admin/delete', DeleteHandler),
	], debug=True)
	wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
