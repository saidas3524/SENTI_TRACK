import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from Crypto.Hash import SHA256
from tornado import gen
from bson.objectid import ObjectId
from validate_email import validate_email
import hashlib
from hashlib import sha1

import os.path
import motor
import pymongo
import hashlib
import datetime
import time
import re

class FilterHandler(tornado.web.RequestHandler):
	@tornado.web.asynchronous
	@gen.coroutine
	def get(self):
		if self.get_secure_cookie('email'):
			email = self.get_secure_cookie('email')
			users_coll=self.application.db.users
			filters_coll = self.application.db.filters
			filters = []
			user = yield users_coll.find_one({"email":email})
			if user:
				for filter in user['tracking']:
					filter = yield filters_coll.find_one({"name":filter})
					if filter:
						filters.append(filter)
				self.render("forms.html",user=user,filters=filters)
			else:
				self.redirect("/404")
		else:
			self.redirect("/")

class AddFilterHandler(tornado.web.RequestHandler):
	@tornado.web.asynchronous
	@gen.coroutine
	def get(self):
		if self.get_secure_cookie("email"):
			email = self.get_secure_cookie("email")
			users_coll=self.application.db.users
			user = yield users_coll.find_one({"email":email})
			u_email =  self.get_argument("email")
			filter = self.get_argument("filter")
			filter = filter.lower()
			if u_email == email:
				filters_coll = self.application.db.filters
				fil = dict()
				fil["name"] = filter
				fil["scores"] = []
				fil["timestamp"] = time.time()
				found_in_filters = yield filters_coll.find_one({"name":filter})
				if not found_in_filters:
					fil["count"] = 1
					yield filters_coll.insert(fil)
				else:
					found_in_filters["count"] += 1
					yield filters_coll.save(found_in_filters)
				if not filter in user["tracking"]:
					user["tracking"].append(filter)
					yield users_coll.save(user)
				response = { 'status': 'success'}
				# self.write(response)
			else:
				response = { 'status': 'failure'}
				# self.write(response)

class DeleteFilterHandler(tornado.web.RequestHandler):
	@tornado.web.asynchronous
	@gen.coroutine
	def get(self):
		if self.get_secure_cookie("email"):
			email = self.get_secure_cookie("email")
			users_coll=self.application.db.users
			user = yield users_coll.find_one({"email":email})
			filters_coll = self.application.db.filters
			name = self.get_argument("name")
			filter = yield filters_coll.find_one({"name":name})
			if filter:
				if filter["name"] in user["tracking"]:
					user["tracking"].remove(filter["name"])
					filter["count"] -= 1
					yield users_coll.save(user)
					yield filters_coll.save(filter)
				if filter["count"] == 0:
					yield filters_coll.remove({"name":name})
				response = { 'status': 'success'}
				self.write(response)
			else:
				response = { 'status': 'failure'}
				self.write(response)
		else:
			response = { 'status': 'failure'}
			self.write(response)
