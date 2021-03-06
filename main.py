# Copyright 2016 Google Inc.
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

from google.appengine.ext import ndb
import webapp2
import jinja2
import json
import logging
import os
import hashlib
import urllib
import time
from google.appengine.api import urlfetch
from google.appengine.ext.webapp import template


CLIENT_ID = '1012960989992-artvdo3rfhmhjpq8p2it2443anbdk9er.apps.googleusercontent.com'
CLIENT_SECRET = 'sMrKM6pYJfPtBnV_dle_uqYL'
REDIRECT_URI = 'https://finalproject-197018.appspot.com/oauth'
GOOGLE_URL = "https://accounts.google.com/o/oauth2/v2/auth"

# [START State declaration]
class State(ndb.Model):
    id = ndb.StringProperty(),
    state = ndb.StringProperty()
# [END State declaration]

# [START Car declaration]
class Car(ndb.Model): #set up the structure of car data
    id = ndb.StringProperty()
    year = ndb.StringProperty()
    make = ndb.StringProperty()
    model = ndb.StringProperty()
    in_space = ndb.BooleanProperty()
    owner_id = ndb.StringProperty()
# [END Car declaration]

# [START Space declaration]
class Space(ndb.Model): #set up the structure of space data
    id = ndb.StringProperty()
    number = ndb.IntegerProperty()
    current_car = ndb.StringProperty()
    arrival_date = ndb.StringProperty()
# [END Space declaration]

def sendErrorResponse(x, status, message):
    x.response.headers.add('Content-Type', 'Application/JSON')
    x.response.set_status(status)
    r = {}
    r['message'] = message
    x.response.write(json.dumps(r))

def sendSuccessResponse(x, status, d):
    x.response.headers.add('Content-Type', 'Application/JSON')
    x.response.set_status(status)
    x.response.write(json.dumps(d))

def getUserEmail(token):
    auth_header = 'Bearer ' + token
    headers = {
            'Authorization' : auth_header
    }

    result = urlfetch.fetch(url="https://www.googleapis.com/plus/v1/people/me", headers=headers, method=urlfetch.GET)
    time.sleep(0.2) #wait a little bit for the request to finish
    results = json.loads(result.content)
    plusUser = results['isPlusUser']
    
    if (plusUser == True):
        email_address = results['emails'][0]['value']
    else:
	email_address = 'anonymous'

    return email_address
	
def checkAuth(x):
    headers = x.request.headers #grab the header of the request
    if ('Authorization' in headers.keys()):
	token = headers['Authorization']
    else:
	return -1

    auth_header = 'Bearer ' + token
    headers = {
            'Authorization' : auth_header

    }

    result = urlfetch.fetch(url="https://www.googleapis.com/plus/v1/people/me", headers=headers, method=urlfetch.GET)
    time.sleep(0.2)
    results = json.loads(result.content)
    if ('error' in results):
        return 0
    else:
        return 1

# [START CarHandler]
class CarHandler(webapp2.RequestHandler):
    # [START post handler]
    def post(self): #post request handler
    	#first check if Authorization token is procided
    	isAuthorized = checkAuth(self)
    	if (isAuthorized == -1):
            sendErrorResponse(self, 400, "No authorization token provided")
            return
    	elif (isAuthorized == 0):
            sendErrorResponse(self, 400, "Invalid token provided")
            return
    	else:
	    #next validate inputs
	    car_data = json.loads(self.request.body) #grab the body of the request
            if ('year' in car_data.keys()):
                yearVar = car_data['year']
            else:
                yearVar = ""
            if ('make' in car_data.keys()):
                makeVar = car_data['make']
            else:
                makeVar = ""
	    if ('model' in car_data.keys()):
                modelVar = car_data['model']
	    else:
                modelVar = ""
	    if (yearVar == "" or makeVar == "" or modelVar == ""): #set up a response if incomplete data is sent
                sendErrorResponse(self, 400, "Year, Make, and Model are all required")
                return
	    else: #if complete data is supplied, grab user data from Google plus, then create the Car
                email = getUserEmail(self.request.headers['Authorization'])
                new_car = Car(id="", year=yearVar, make=makeVar, model=modelVar, in_space=False, owner_id=email) 
                #assign values 
                new_car.put() #save the fields we have
                new_car.id = str(new_car.key.id()) #get the id generated by datastore
                new_car.put() #save the id to the car we created
                car_dict = new_car.to_dict() #convert to a dictionary
                car_dict['self'] = '/cars/' + new_car.key.urlsafe() #add self element to dictionary
                sendSuccessResponse(self, 200, car_dict)
                return

    # [END post handler]	
# [END CarHandler]

class MainPage(webapp2.RequestHandler):
	def get(self):
		state = hashlib.sha256(os.urandom(1024)).hexdigest()  # generate a random key
	#	template_values = {
	#		'state': state
	#	}

		# save the key to the datastore for later comparison
		new_key = State(id="", state=state)
		new_key.put()
		new_key.id = str(new_key.key.id())
		new_key.put()
		# create the url to be called to redirect for login
		url = GOOGLE_URL + "?response_type=code&client_id=" + CLIENT_ID + "&redirect_uri=" + REDIRECT_URI + "&scope=email&state=" + state

		# create value to inject into html page
		page_values = {'url': url}

		# display the html page
		path = os.path.join(os.path.dirname(__file__), 'pages/mainPage.html')

		# inject the url into the url variable in the html
		# self.response.write(page_values)
		self.response.write(template.render(path, page_values))
		#template = JINJA_ENVIRONMENT.get_template('mainPage.html')
		#self.response.write(template.render(template_values))


# [START OAuthHandler]
class OAuthHandler(webapp2.RequestHandler):
    def get(self):
        #self.response.write("hello oauht")
        state = self.request.get('state')  # get the state sent back
        code = self.request.get('code')  # get the code sent by server
        #good_req = 0

	#qry = State.query()
	#qryResults = qry.fetch()
	#for x in qryResults:  # for each key in the data store, compare the state we got back
	 #   if (x.state == state):
          #      good_req = 1
           #     stateId = x.id
            #    ndb.Key("State", long(x.key.id())).delete()
	
#	self.response.write(state)
	
	#if (good_req == 1):
        client_id = "1012960989992-artvdo3rfhmhjpq8p2it2443anbdk9er.apps.googleusercontent.com"
        client_secret = "sMrKM6pYJfPtBnV_dle_uqYL"
        redirect_uri = "https://finalproject-197018.appspot.com/oauth"
        post_body = {  # set up the post request to get the token
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }

	# execute post request
        payload = urllib.urlencode(post_body)
        headers = {'Content-Type':'application/x-www-form-urlencoded'} 
        #send data to get the info
        result = urlfetch.fetch(url="https://www.googleapis.com/oauth2/v4/token", payload=payload, method=urlfetch.POST, headers = headers)
    	#time.sleep(0.3)  # wait a little bit for the request to finish
        json_result = json.loads(result.content)         
        headers = {'Authorization': 'Bearer ' + json_result['access_token']}
        token = json_result['access_token']    
        #on to the google plus API
        result = urlfetch.fetch(url="https://www.googleapis.com/plus/v1/people/me", method = urlfetch.GET, headers=headers)
        json_result = json.loads(result.content)
        fname = json_result['name']['givenName']
        lname = json_result['name']['familyName']

       # results = json.loads(result.content)
			
			
        template_values = {
            'fname': fname,
            'lname': lname,
            'state': state,
            'token': token
        }

	# display the html page
	path = os.path.join(os.path.dirname(__file__), 'pages/oauthPage.html')

	# inject the url into the url variable in the html
	self.response.write(template.render(path, template_values))
              
	#else:
	 #   self.response.write("bad request")


# [END OAuthHandler]

allowed_methods = webapp2.WSGIApplication.allowed_methods
new_allowed_methods = allowed_methods.union(('PATCH',))
webapp2.WSGIApplication.allowed_methods = new_allowed_methods

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/oauth', OAuthHandler),
    ('/cars', CarHandler),
    ('/cars/([\w|-]*)', CarHandler)
], debug=True)
