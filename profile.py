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
import nltk
import enchant

d = enchant.Dict("en_US")

ignore = ["CC","CD","DT","EX","FW","IN","NN","NNP","NNS","NNPS","PRP","PRP$","SYM","TO","UH","RP","-NONE-"]

def remove_repeat(word):
	word+="&"
	old = None
	count = 0
	for letter in word:

		if old == None:
			old = letter

		if letter == old:
			count += 1
			old = letter

		else:
			if count > 2:
				current = old*(count+1)
				new = old*2
				word = word.replace(current,new)
			count = 0
			old = letter
	word = word[:-1]

	if not d.check(word):
		suggestion_found = 0
		suggestions = d.suggest(word)
 		for suggestion in suggestions:
			letter_not_found = 0
			for letter in word:
				if not letter in suggestion:
					letter_not_found = -1
			if letter_not_found == 0:
				word = suggestion
				suggestion_found = 1
				break
		if suggestion_found == 0:
			if len(suggestions)>0:
				word = suggestions[0]
	return word

def correct(word):
		new_words = ""
		if d.check(word):
			new_word = word
		else:
			word = remove_repeat(word)
			new_word = word
		return new_word

def sentiment(word_scores,inverse):
	n_count = 0
	negative_score = 0
	p_count = 0
	positive_score = 0
	ne_count = 0
	neutral_score = 0
	for word in word_scores:
		if word[1] > 60:
			positive_score += word[1]
			p_count += 1
		elif word[1] < 40 and word[1]>0:
			negative_score += (100 - word[1])
			n_count += 1
		else:
			neutral_score += word[1]
			ne_count += 1

	if p_count > 0:
		p_prob = round(positive_score/p_count,2)
	else:
		p_prob = 0

	if n_count > 0:
		n_prob = round(negative_score/n_count,2)
	else:
		n_prob = 0

	if ne_count > 0:
		ne_prob = round(neutral_score/ne_count,2)
	else:
		ne_prob = 0

	if positive_score > negative_score:
		if positive_score>neutral_score:
			if not inverse:
				return ("positive",p_prob)
			else:
				return ("negative",p_prob)
		else:
			return ("neutral",ne_prob)
	else:
		if negative_score>neutral_score:
			if not inverse:
				return ("negative",n_prob)
			else:
				return ("positive",n_prob)
		else:
			return ("neutral",ne_prob)


class LoginHandler(tornado.web.RequestHandler):
	def get(self):
		if self.get_secure_cookie("email"):
			self.redirect(self.get_argument('next', '/'))
		else:
			next = self.get_argument('next', '/')
			self.render("login.html",message="none",next=next)

	@tornado.web.asynchronous
	@gen.coroutine
	def post(self):
		users_coll = self.application.db.users
		email = self.get_argument("email")
		password = self.get_argument("password")
		next = str(self.get_argument("next"))
		user = yield users_coll.find_one({"email":email})
		if user:
			password = SHA256.new(password).hexdigest()
			if password == user["password"]:
				self.set_secure_cookie("email",email)
				self.redirect("/")
			else:
				self.render("login.html",message="wrong",next=next)
		else:
			self.render("login.html",message="no",next=next)


class RegisterHandler(tornado.web.RequestHandler):
	def get(self):
		self.render("register.html",message="none")

	@tornado.web.asynchronous
	@gen.coroutine
	def post(self):
		users_coll = self.application.db.users
		name = self.get_argument("q1")
		email = self.get_argument("q2")
		password = self.get_argument("q3")
		password = SHA256.new(password).hexdigest()
		user = yield users_coll.find_one({"email":email})
		if not validate_email(email) or len(name) == 0 or len(password) == 0:
			self.render("register.html",message="error")
		if user:
			self.render("register.html",message="exists")
		else:
			user = dict()
			user["name"] = name
			user["email"] = email
			user["password"] = password 
			user["timestamp"] = time.time()
			user["tracking"] = []
			yield users_coll.insert(user)
			self.set_secure_cookie("email", email)
			self.redirect("/")

class homehandler(tornado.web.RequestHandler):
	@tornado.web.asynchronous
	@gen.coroutine
	def get(self):
		if self.get_secure_cookie("email"):
			filter = self.get_argument("filter","/")
			users_coll = self.application.db.users
			filters_coll = self.application.db.filters
			email = self.get_secure_cookie("email")
			user = yield users_coll.find_one({"email":email})

			if user:
				if filter == "/" and len(user['tracking'])>0:
					filter = user['tracking'][0]
				filter = yield filters_coll.find_one({"name":filter})
				if filter:
					filter['total'] = len(filter['scores'])
					filter['positive'],filter['negative'],filter['neutral'] = (0,0,0)
					for score in filter['scores']:
						if score[0] == "positive":
							filter['positive'] += 1
						elif score[0] == "negative":
							filter['negative'] += 1
						else:
							filter['neutral'] += 1
					self.render("home.html",user=user,filter=filter)
				else:
					self.render("r-home.html",user=user,filter=filter)
		else:
			self.render("index.html")

class ProfileHandler(tornado.web.RequestHandler):
	@tornado.web.asynchronous
	@gen.coroutine
	def get(self):
		if self.get_secure_cookie('email'):
			email = self.get_secure_cookie('email')
			users_coll=self.application.db.users
			user = yield users_coll.find_one({"email":email})
			if user:
				self.render("profile.html",user=user)
			else:
				self.redirect("/404")
		else:
			self.redirect("/")

	@tornado.web.asynchronous
	@gen.coroutine
	def post(self):
		if self.get_secure_cookie('email'):
			email=self.get_secure_cookie('email')
			users_coll=self.application.db.users
			user = yield users_coll.find_one({'email':email})
			if user:
				hide = self.get_argument('hide')
				oldpass = self.get_argument('oldpas')
				newpass = self.get_argument ('newpas')
				if not oldpass=="1":
					if hide ==  email and user["password"] == SHA256.new(oldpass).hexdigest() and not newpass=="1":
						user["email"] = self.get_argument('email')
						user["name"] = self.get_argument('name')
						user["password"] = SHA256.new(newpass).hexdigest()
						yield users_coll.save(user)
						self.redirect("/profile")
					else:
						self.redirect("/")
				else:
					user["email"] = self.get_argument('email')
					user["name"] = self.get_argument('name')
					yield users_coll.save(user)
					self.redirect("/profile")	
			else:
				self.redirect("/")

class LogoutHandler(tornado.web.RequestHandler):
	@tornado.web.asynchronous
	@gen.coroutine
	def get(self):
		if self.get_secure_cookie("email"):
			self.clear_cookie("email")
			self.redirect("/")
		else:
			self.redirect("/")

class ChartsHandler(tornado.web.RequestHandler):
	@tornado.web.asynchronous
	@gen.coroutine
	def get(self):
		if self.get_secure_cookie('email'):
			email = self.get_secure_cookie('email')
			users_coll=self.application.db.users
			user = yield users_coll.find_one({"email":email})
			if user:
				self.render("charts.html",user=user)
			else:
				self.redirect("/404")
		else:
			self.redirect("/")

class ClassifyHandler(tornado.web.RequestHandler):
	@tornado.web.asynchronous
	@gen.coroutine
	def get(self):
		scores = "0"
		self.render("classify.html",scores=scores,text="",w_scores="")

	def post(self):
		uri = "mongodb://akshay:akshay@ds043329.mongolab.com:43329/senti"
		client = pymongo.MongoClient(uri)
		db = client.senti
		scores = db.scores
		text_o = self.get_argument("text")
		total_neg_tweets = 1229344
		total_pos_tweets = 753391
		total_tweets = 1982735

		p_of_c = 0.3799
		# total_pos_words = 1605239
		# total_neg_words = 2975410
		# total_words = 4580649

		total_pos_words = 1513035
		total_neg_words = 2753783 
		total_words = 4266818
		text = text_o.replace("."," ")
		text = text.split(" ")
		w_scores = []
		final_pos = 0
		final_total = 0
		inverse = False
		for word in text:
			if len(word) > 0:
				word1 = correct(str.lower(word.encode("ascii","ignore")))
				if word1 == "not":
					inverse = True
				score = scores.find_one({"word":word1})
				if score:
					p_of_d_given_c = float(score['pos'])/total_pos_words
					p_of_d = (float(score['pos']) + float(score['neg']))/total_words
					p_of_c_given_d = round(p_of_c * p_of_d_given_c / p_of_d,4)
					w_scores.append((word,p_of_c_given_d*100))
				else:
					w_scores.append((word,0))
		senti = sentiment(w_scores,inverse)
		self.render("classify.html",scores="123",text=text_o,w_scores=w_scores,sentiment=senti)



#Using Gravatars for profile picture
class Gravatar(tornado.web.UIModule):
    def render(self, email, size=40, image_type='jpg'):
        """
        Gets profile picture from gravatar.
        :param email: Email ID of the User.
        :param size: Size of the picture.
        :param image_type: Type of the image file.
        :return: Link to the Gravatar profile picture of the user.
        """
        email_hash = hashlib.md5(email).hexdigest()
        return "http://gravatar.com/avatar/{0}?s={1}.{2}".format(email_hash, size, image_type)











