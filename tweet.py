import pymongo
#Import the necessary methods from tweepy library
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream

import time
import re
import nltk
import enchant



#Variables that contains the user credentials to access Twitter API 
access_token = "101420632-0aVyyI88sLm7aMSPYRK3Ks5GAc6oMTB3Au136QGU"
access_token_secret = "Sdh4Mt4KO2TiCKpoVPxaVMCtHviIyEzu7Jq8VfBcUGBnF"
consumer_key = "5Gv9FmRSMDuywpyrynkRvV2xn"
consumer_secret = "Ktl8tDnOQk4bpj0dcjDpc1UebmKaHtaGkhskRfQeLktXXDlPRX"



uri = "mongodb://akshay:akshay@ds043329.mongolab.com:43329/senti"
client = pymongo.MongoClient(uri)
db = client.senti
filters = db.filters

old_length = 0

filts = []
for filter in filters.find():
    name = filter['name'].encode("ascii","ignore")
    filts.append(str.lower(name))
    filts.append(str.upper(name))
    filts.append(str.capitalize(name))

print filts

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


def Classify(string):
    for filter in filts:
        if filter in string:
            scores = db.scores
            filters = db.filters
            text_o = string
            total_neg_tweets = 1229344
            total_pos_tweets = 753391
            total_tweets = 1982735

            p_of_c = 0.3799
            
            total_pos_words = 1513035
            total_neg_words = 2753783 
            total_words = 4266818
            text = re.sub(r'\W+', ' ', text_o)
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
            name = str.lower(filter)
            filter = filters.find_one({"name":str.lower(name)})
            if filter:
                filter['scores'].append((senti[0],time.time()))
                filters.save(filter)
                print str.lower(name),senti[0]

def start_searching(filters):
    global old_length
    old_length = len(filters)
    l = StdOutListener()
    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    stream = Stream(auth, l)

    #This line filter Twitter Streams to capture data by the keywords: 'python', 'javascript', 'ruby'
    stream.filter(track=filters)
    l.keep_scoring()

#This is a basic listener that just prints received tweets to stdout.
class StdOutListener(StreamListener):

    def on_data(self, data):
        data = data.encode("ascii","ignore")
        start = str.find(data,"text")
        end = str.find(data,"source")
        data = data[start+7:end-3]
        if data[0:2] == "RT":
            start = str.find(data,":")
            data = data[start+1:]
        Classify(data)
        filts = []
        for filter in filters.find():
            name = filter['name'].encode("ascii","ignore")
            filts.append(str.lower(name))
            filts.append(str.upper(name))
            filts.append(str.capitalize(name))
        if len(filts) != old_length:
            print filts
            start_searching(filts)
        return True

    def on_error(self, status):
        print status

    def keep_scoring(self):
        while True:
            print "Yes"

if __name__ == '__main__':
    #This handles Twitter authetification and the connection to Twitter Streaming API
    start_searching(filts)
    
        