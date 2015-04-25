import pymongo
import sys

uri = "mongodb://akshay:akshay@ds043329.mongolab.com:43329/senti"

client = pymongo.MongoClient(uri)

db = client.senti

scores = db.scores



for line in sys.stdin:
	data = line.strip().split("\t")

	if len(data)<3:
		continue

	tweet,neg,pos= data

	word = dict()
	word['word'] = tweet
	word['neg'] = neg
	word['pos'] = pos

	scores.insert(word) 
	print tweet