import os.path
import motor
import pymongo
import hashlib
from TwitterAPI import TwitterAPI

#Import the necessary methods from tweepy library
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

import profile
import filter

from tornado.options import define,options

define("port",default=8000,help="runs on the given port")

#Variables that contains the user credentials to access Twitter API 
# access_token = "101420632-0aVyyI88sLm7aMSPYRK3Ks5GAc6oMTB3Au136QGU"
# access_token_secret = "Sdh4Mt4KO2TiCKpoVPxaVMCtHviIyEzu7Jq8VfBcUGBnF"
# consumer_key = "5Gv9FmRSMDuywpyrynkRvV2xn"
# consumer_secret = "Ktl8tDnOQk4bpj0dcjDpc1UebmKaHtaGkhskRfQeLktXXDlPRX"

MONGODB_URI = "mongodb://akshay:akshay@ds043329.mongolab.com:43329/senti"


#This is a basic listener that just prints received tweets to stdout.
# class StdOutListener(StreamListener):

#     def on_data(self, data):
#         data = data.encode("ascii","ignore")
#         start = str.find(data,"text")
#         end = str.find(data,"source")
#         data = data[start+7:end-3]
#         if data[0:2] == "RT":
#             start = str.find(data,":")
#             data = data[start+1:]
#         print data
#         return True

#     def on_error(self, status):
#         print status


# class TweepyHandler(tornado.web.RequestHandler):
# 	def get(self):
# 		l = StdOutListener()
# 		auth = OAuthHandler(consumer_key,consumer_secret)
# 		auth.set_access_token(access_token,access_token_secret)
# 		stream = Stream(auth,l)
# 		stream.filter(track=["CBIT"])




# class tweethandler(tornado.web.RequestHandler):
# 	def get(self):
# 		consumer_key = '5Gv9FmRSMDuywpyrynkRvV2xn'
# 		consumer_secret = 'Ktl8tDnOQk4bpj0dcjDpc1UebmKaHtaGkhskRfQeLktXXDlPRX'
# 		access_key = '101420632-0aVyyI88sLm7aMSPYRK3Ks5GAc6oMTB3Au136QGU'
# 		access_secret = 'Sdh4Mt4KO2TiCKpoVPxaVMCtHviIyEzu7Jq8VfBcUGBnF'
# 		query = self.get_argument("q")
# 		api=TwitterAPI(consumer_key,consumer_secret,access_key,access_secret)
# 		result=api.request('search/tweets',{'q':query})
# 		tweets  = []
# 		for item in result:
# 			tweets.append(item['text'])
# 		self.render("tweets.html",tweets=tweets)


class Application(tornado.web.Application):
	def __init__(self):
		"""
			initialises the Application
		"""
		handlers=[
		(r"/",profile.homehandler),
		(r"/login",profile.LoginHandler),
		(r"/register",profile.RegisterHandler),
		(r"/logout",profile.LogoutHandler),
		(r"/charts",profile.ChartsHandler),
		(r"/profile",profile.ProfileHandler),
		(r"/classify",profile.ClassifyHandler),
		(r"/filter",filter.FilterHandler),
		(r"/add_filter",filter.AddFilterHandler),
		(r"/delete_filter",filter.DeleteFilterHandler),
		]
		settings=dict(
			template_path=os.path.join(os.path.dirname(__file__),"templates"),
			static_path=os.path.join(os.path.dirname(__file__),"static"),
			ui_modules={
                "Gravatar": profile.Gravatar
            },
			cookie_secret="bZJc2sWbQLKos6GkHn/VB9oXwQt8S0R0kRvJ5/xJ89E=",
			xsrf_cookies=True,
			login_url="/login",
			debug=True
			)
		client1 = pymongo.MongoClient(MONGODB_URI)
		client = motor.MotorClient(MONGODB_URI)
		self.db = client.senti
		self.db1 = client1.senti
		tornado.web.Application.__init__(self,handlers,**settings)

if __name__=="__main__":
	tornado.options.parse_command_line()
	http_server=tornado.httpserver.HTTPServer(Application(),xheaders=True)
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()

