"""
API Module

Handles everything for connecting to and interacting with the API.
"""

import requests
from requests.exceptions import HTTPError, Timeout
import json
import logging
import time
from time import sleep

#Used to transform query parameters like "thing = this" to something the API understands
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

#from .exception import *


class Connection:
    r"""Base class to setup connections and access other objects

    :param store_file: Path to JSON file containing parameters
    :return: :class:`connection <connection>` object

    """
    #def __init__(self, store_data, credentials, codes_file):
    #Lets only take a config file, and process everything based on that
    def __init__(self, store_datafile):
                
        # Because refresh tokens don't expire quickly, we save them locally so we can grab them again later.
       #pulling this out to make it work with multiple clients and support Gaspars
        
        self.load_store(store_datafile)
        
        logging.info(f"LSRETAIL_API: Creating new Lightspeed Connection with {store_datafile} (Store: {self.account_id})")
        
        # A reminder on how Lightspeed tokens work:
        # Temporary token (CODE) - A temp token generated when a user authenticates to lightspeed. It is returned in the URL as code= and called code when passed to the lightspeed api
        # Refresh token (refresh_token) - Does not expire and should be saved (you can also see them in the Lightspeed UI under Settings > Client API Access > API Client
        #                                 The refresh_token is used to get a new, fresh access_token
        # Access token (access_token) - Used to actually get info from the API. Access tokens expire (expires_in) and need to be checked and periodically refreshed by
        #                               using the refresh_token
        # So you first have a user authenticate with their username and password which gives you CODE, you use CODE to get a new refresh_token and access_token, and you use
        # the refresh_token to periodically get new/refresh the access_token, and you use the access_token to actually get things from the API. Whew.


        self.access_token_url = "https://cloud.lightspeedapp.com/oauth/access_token.php"
        self.access_token = ''  
        self.expires_in = ''
        self.response = None
        self.request_counter = 0
        self.refresh_token=""
        self.timeout = 7.0  # need to catch timeout?
        
        self.token_refresh()
        self._session = requests.Session()
    
    def load_store(self,store_datafile):
        """Uses a json config file to set key variables to manage connection and output paths"""

        with open(store_datafile) as f:
            store_data = json.load(f)
        
        self.account_id = store_data['account_id']
        self.codes_path = store_data['codes_path']
        self.client_id = store_data['client_id']
        self.client_secret = store_data['client_secret']
        self.api_key = store_data['api_key'],
        self.api_secret = store_data['api_secret'],

        self.api_url = f"https://api.lightspeedapp.com/API/Account/{store_data['account_id']}/"
        self.codes_file = store_data['codes_file']
        self.export_path = store_data['export_path']
        self.database = store_data["database"]
            
        return
    
    @staticmethod
    def flatten_json(y):
        out = {}

        def flatten(x, name=''):
            if type(x) is dict:
                for a in x:
                    flatten(x[a], name + a + '_')
            elif type(x) is list:
                i = 0
                for a in x:
                    flatten(a, name + str(i) + '_')
                    i += 1
            else:
                out[name[:-1]] = x
        flatten(y)
        return out

    def token_refresh(self):
        # On initiation, the object checks to see if there are codes (access_token and refresh_token) saved locally. If it finds them, it reads them, assigns them to 
        # properties, refreshes them if needed, and returns
        # 1. Check to see if there is a credentials.json already
        logging.info(f"LSRETAIL_API: Hold while the token is refreshed...")
        try:
            with open(self.codes_file,'r') as f:
                codes = json.load(f)
                # Your refresh token does not expire, so it is actually the important one.
                logging.debug(f"LSRETAIL_API: REFRESH TOKEN: Found codes.json with refresh_token : {codes['refresh_token']}")
        except FileNotFoundError as err:

            # TODO: Need to add back in the code that checks the environment variables for keys. This should handle both env and file keys
            logging.warning("No Codes File Found:{0}".format(err))
            # 2. If there are no keys, it should fire the process to get a temp token, authenticate the user, and write out the creds
            # For now we are going to do it manually by going to
            # https://cloud.lightspeedapp.com/oauth/authorize.php?response_type=code&client_id={YOUR CLIENT ID}&scope=employee:all
            # to obtain the CODE. Paste that CODE (it is in the URL returned) below and run this before the CODE expires (30 seconds)
            # to get your access token back.
            CODE = "baee95ac124ca0eabcfcb6061526b21a20844f2c" 
            # This is the payload defined by the Lightspeed API doc. My code differs from the sample code, but I think their samples have
            # issues, so mostly I don't use them. 
            payload = {
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'code': CODE,
                    'grant_type':'authorization_code'
                    }
            # Send the payload to the API access token URL
            r = requests.post(self.access_token_url, data=payload)
            codes = r.json()
            logging.debug("REFRESH TOKEN: Got new codes, which are: %s" % (codes)) 

            # Save the codes in a file on the local system so we can get them (and refresh them) next time  
            with open(self.codes_file, 'w') as outfile:  
                json.dump(r.json(), outfile, indent=4)
        else:
            # If there are codes, get the refresh token out, and force a refresh the access code            
            self.refresh_token = codes['refresh_token']
            # TODO - This should probably check the expiration but for now I am forcing a refresh. Need to come back and write some checking
            payload = {
                'refresh_token': self.refresh_token,
                'client_secret': self.client_secret,
                'client_id': self.client_id,
                'grant_type': 'refresh_token',
            }
            codes = requests.post(self.access_token_url, data=payload).json()
            self.access_token = codes['access_token']
            self.token_type = codes['token_type']
            self.scope = codes['scope']
            self.expires_in = codes['expires_in']
            self.expires = time.time() + int(self.expires_in)
            logging.debug(f"REFRESH TOKEN: Token refreshed, expires in {self.expires_in} seconds")
            #logging.debug("Writing out new refreshed codes which are now: %s" % (codes))
            # The data returned in a refresh doesn't include the refresh_token, and we need to update the codes.json file, so rebuild it and write it out to the file
            # TODO - Need to look up the way to append to a dictionary - probably don't need to rebuild the whole thing
            new_codes = {
                    "access_token": codes['access_token'],
                    "expires_in": codes['expires_in'],
                    "token_type": codes['token_type'],
                    "scope": codes['scope'],
                    "refresh_token": self.refresh_token,
                    "last_run": time.time()
                    }
            with open(self.codes_file, 'w') as outfile:  
                json.dump(new_codes, outfile, indent=4)

            
            # Now we have nice, fresh codes we can buld the headers property that the API will use
            self.headers = {'authorization' : f'Bearer {self.access_token}'}
            logging.debug(f"REFRESH TOKENS: Headers are now : {self.headers}")


    def _manage_rate(self):
               
        #Take a look at the response header, and get some variables we can use
        #logging.debug(self.response.headers)
        if self.response is None:
            self.token_refresh()
            return
        
        api_drip_rate = float(self.response.headers['X-LS-API-Drip-Rate'])
        # Since the bucket level comes back as a fraction, we pull it appart to get the pieces we need
        api_bucket_level, api_bucket_size = [(float(x)) for x in self.response.headers['X-LS-API-Bucket-Level'].split('/')]

        logging.debug(f"MANAGE RATE: Used {api_bucket_level} of {api_bucket_size} , refreshing at {api_drip_rate} and {time.time()-self.expires} sec. left on token.")
            
        if api_bucket_size < api_bucket_level + 10:
            logging.info(f"MANAGE RATE: Bucket is almost full, taking a break.")
            sleep(10)
        
        if time.time() >= self.expires :
            logging.debug(f"MANAGE RATE: Token needs a refresh")
            sleep(5) #Make sure lightspeed has timed out
            self.token_refresh()


    def list(self, resource, filter = "", offset = 0, limit = 100, rows = 0, flatten=False):
        
        self._manage_rate()
        querystring = {'offset':offset, 'limit':limit}
        all_resources = []
        try:

            if filter == "":
                url = self.api_url + resource + '.json'
            else:
                #TODO: This needs to handle escaping the filter characters
                url = self.api_url + resource + '.json?' + filter
            
            self.response = requests.get(url, params=querystring, headers=self.headers)
            self.response.raise_for_status()

            logging.debug(f"Request Status Code: {self.response.status_code}")
            # And hold just the json returned in all_data
            all_data = self.response.json()

            # Lightspeed API always returns two top level results in the json - the @attributes which includes count, offset, and limit, 
            # and a second block that actually has the thing from the API. 
            attributes = all_data['@attributes']
            
            if attributes["count"]  == '0': return all_resources # Should probably do something better here. If the filter is returning no rows this is failing - need to handle more gracefully.
            all_resources = all_data[resource]

            # We can get the total number of things that are returned from the [@attributes][count]
            # We need to use these as integers so we can loop, so convert them
            total_amount = int(all_data['@attributes']['count'])
            current_offset = int(all_data['@attributes']['offset']) + int(all_data['@attributes']['limit'])
            current_limit = int(all_data['@attributes']['limit'])
            
            #Loop through the resources to build the full list
            while total_amount >= current_offset:
                self._manage_rate()
                querystring = {'offset':current_offset, 'limit':current_limit}
                self.response = requests.get(url, params=querystring, headers=self.headers)
                self.response.raise_for_status()
                all_data = self.response.json()
                all_resources.extend(all_data[resource])
                current_offset = current_offset + current_limit
            logging.info(f'LIST: Returned {total_amount} of {resource} with {filter}')



                        
        # Errors from lightspeed doc at: https://developers.lightspeedhq.com/retail/introduction/errors/
        except requests.exceptions.HTTPError as err:
            print(err)    
            if err.response.status_code == 400:
                logging.error(f"{err.response.status_code}: Bad Request: Progably a client error (ie. malformed query or invalid XML/JSON payload): {err.response.headers}")
            elif err.response.status_code == 401:           
                logging.error(f"{err.response.status_code}: Unauthorized: Auth was required but failed: {err.response.headers}")
            elif err.response.status_code == 403:           
                logging.error(f"{err.response.status_code}: Forbidden: Invalid request, server refused: {err.response.headers}")       
            elif err.response.status_code == 404:           
                logging.error(f"{err.response.status_code}: Not Found: Probably a typo in the endpoint name: {err.response.headers}")
            elif err.response.status_code == 405:           
                logging.error(f"{err.response.status_code}: Method Not Allowed: Request method not supported, check that target supports GET/PUT/POST/whatever you did:  {err.response.headers}")
            elif err.response.status_code == 409:           
                logging.error(f"{err.response.status_code}: Conflict: Request could not be processed because of conflict:  {err.response.headers}")
            elif err.response.status_code == 422:           
                logging.error(f"{err.response.status_code}: Unprocessable Entity: The request was well-formed but was unable to be followed due to semantic errors:  {err.response.headers}")
            elif err.response.status_code == 429:           
                logging.error(f"{err.response.status_code}: Too Many Requests: Exceeded the rate limit:  {err.response.headers}")
            elif err.response.status_code == 500:           
                logging.error(f"{err.response.status_code}: Internal Error: Unexpected condition and the server freaked:  {err.response.headers}")
            elif err.response.status_code == 502:           
                logging.error(f"{err.response.status_code}: Bad Gateway: Invalid response from upstream server:  {err.response.headers}")
            elif err.response.status_code == 503:           
                logging.error(f"{err.response.status_code}: Service Unavailable: server overload or down for maintenance:  {err.response.headers}")  
            else:
                logging.error(f"{err.response.status_code}: Unhandled Exception: don't know what to do:  {err.response.headers}")
        # finally:
        #      return {'status_code': self.response.status_code, 'headers': self.response.headers}
            
         #TODO: This fails on erro 500. Test more with incorrect filters.   
        if flatten:
            return self.flatten_json(dict(all_resources))
        else:
            return all_resources   #self.response.json()
    

    def _run_method(self, method, resource, data=None, query=None):
        """
        Universal handler for all request methods.
        """
        if query is None:
            query = {}
        if data is None:
            data = {}

        url = self.api_url + resource + ".json"

        qs = urlencode(query)
        if qs:
            qs = "?" + qs
        url += qs

        params = {'offset':0, 'limit':100}
        # mess with content
        # if data:
        #     if not headers:  # assume JSON
        #         data = json.dumps(data)
        #         headers = {'Content-Type': 'application/json'}
        #     if headers and 'Content-Type' not in headers:
        #         data = json.dumps(data)
        #         headers['Content-Type'] = 'application/json'
        logging.debug("%s %s" % (method, url))
        # make and send the request

        return self._session.request(method, url, params=params, headers=self.headers)
    
    def _handle_response(self, url, res, suppress_empty=True):
        """
        Returns parsed JSON or raises an exception appropriately.
        """
        result = {}
        if res.status_code in (200, 201, 202):
            try:
                result = res.json()
                return result
            except Exception as e:  # json might be invalid, or store might be down
                e.message += " (_handle_response failed to decode JSON: " + str(res.content) + ")"
                raise  # TODO better exception
        if res.status_code == 400:
            logging.error(f"{res.status_code}: Bad Request: Progably a client error (ie. malformed query or invalid XML/JSON payload): {res.headers}")
        elif res.status_code == 401:           
            logging.error(f"{res.status_code}: Unauthorized: Auth was required but failed: {res.headers}")
        elif res.status_code == 403:           
            logging.error(f"{res.status_code}: Forbidden: Invalid request, server refused: {res.headers}")       
        elif res.status_code == 404:           
            logging.error(f"{res.status_code}: Not Found: Probably a type in the endpoint name: {res.headers}")
        elif res.status_code == 405:           
            logging.error(f"{res.status_code}: Method Not Allowed: Request method not supported, check that target supports GET/PUT/POST/whatever you did:  {res.headers}")
        elif res.status_code == 409:           
            logging.error(f"{res.status_code}: Conflict: Request could not be processed because of conflict:  {res.headers}")
        elif res.status_code == 422:           
            logging.error(f"{res.status_code}: Unprocessable Entity: The request was well-formed but was unable to be followed due to semantic errors:  {res.headers}")
        elif res.status_code == 429:           
            logging.error(f"{res.status_code}: Too Many Requests: Exceeded the rate limit:  {res.headers}")
        elif res.status_code == 500:           
            logging.error(f"{res.status_code}: Internal Error: Unexpected condition and the server freaked:  {res.headers}")
        elif res.status_code == 502:           
            logging.error(f"{res.status_code}: Bad Gateway: Invalid response from upstream server:  {res.headers}")
        elif res.status_code == 503:           
            logging.error(f"{res.status_code}: Service Unavailable: server overload or down for maintenance:  {res.headers}")  
        else:
            logging.error(f"{res.status_code}: Unhandled Exception: don't know what to do:  {res.headers}")
        
        return result

    def get(self, resource="", rid=None, **query):
        """
        Retrieves the resource with given id 'rid', or all resources of given type.

        Keyword arguments can be parsed for filtering the query, for example:
            connection.get('products', limit=3, min_price=10.5)
        (see Bigcommerce resource documentation).
        """
        if rid:
            if resource[-1] != '/':
                resource += '/'
            resource += str(rid)
        response = self._run_method('GET', resource, query=query)
        return self._handle_response(resource, response)

    def update(self, resource, id, data):
        self._manage_rate()
        try:
            url = self.api_url + resource + "/"+ str(id) + '.json'
            self.response = requests.put(url, data=json.dumps(data), headers=self.headers)
            self.response.raise_for_status()


        except requests.exceptions.HTTPError as err:
            print(err)    
            if err.response.status_code == 400:
                logging.error(f"{err.response.status_code}: Bad Request: Progably a client error (ie. malformed query or invalid XML/JSON payload): {err.response.headers}")
            elif err.response.status_code == 401:           
                logging.error(f"{err.response.status_code}: Unauthorized: Auth was required but failed: {err.response.headers}")
                self.refresh_token
            elif err.response.status_code == 403:           
                logging.error(f"{err.response.status_code}: Forbidden: Invalid request, server refused: {err.response.headers}")       
            elif err.response.status_code == 404:           
                logging.error(f"{err.response.status_code}: Not Found: Probably a type in the endpoint name: {err.response.headers}")
            elif err.response.status_code == 405:           
                logging.error(f"{err.response.status_code}: Method Not Allowed: Request method not supported, check that target supports GET/PUT/POST/whatever you did:  {err.response.headers}")
            elif err.response.status_code == 409:           
                logging.error(f"{err.response.status_code}: Conflict: Request could not be processed because of conflict:  {err.response.headers}")
            elif err.response.status_code == 422:           
                logging.error(f"{err.response.status_code}: Unprocessable Entity: The request was well-formed but was unable to be followed due to semantic errors:  {err.response.headers}")
            elif err.response.status_code == 429:           
                logging.error(f"{err.response.status_code}: Too Many Requests: Exceeded the rate limit:  {err.response.headers}")
                sleep(10)
            elif err.response.status_code == 500:           
                logging.error(f"{err.response.status_code}: Internal Error: Unexpected condition and the server freaked:  {err.response.headers}")
            elif err.response.status_code == 502:           
                logging.error(f"{err.response.status_code}: Bad Gateway: Invalid response from upstream server:  {err.response.headers}")
            elif err.response.status_code == 503:           
                logging.error(f"{err.response.status_code}: Service Unavailable: server overload or down for maintenance:  {err.response.headers}")  
            else:
                logging.error(f"{err.response.status_code}: Unhandled Exception: don't know what to do:  {err.response.headers}")
    
    def update_image(self, id, data, files):
        self._manage_rate()
        try:
            url = self.api_url + "Image.json"
            self.response = requests.post(url, files=files, data=data, headers=self.headers)
            self.response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(err)    
            if err.response.status_code == 400:
                logging.error(f"{err.response.status_code}: Bad Request: Progably a client error (ie. malformed query or invalid XML/JSON payload): {err.response.headers}")
            elif err.response.status_code == 401:           
                logging.error(f"{err.response.status_code}: Unauthorized: Auth was required but failed: {err.response.headers}")
                self.refresh_token
            elif err.response.status_code == 403:           
                logging.error(f"{err.response.status_code}: Forbidden: Invalid request, server refused: {err.response.headers}")       
            elif err.response.status_code == 404:           
                logging.error(f"{err.response.status_code}: Not Found: Probably a type in the endpoint name: {err.response.headers}")
            elif err.response.status_code == 405:           
                logging.error(f"{err.response.status_code}: Method Not Allowed: Request method not supported, check that target supports GET/PUT/POST/whatever you did:  {err.response.headers}")
            elif err.response.status_code == 409:           
                logging.error(f"{err.response.status_code}: Conflict: Request could not be processed because of conflict:  {err.response.headers}")
            elif err.response.status_code == 422:           
                logging.error(f"{err.response.status_code}: Unprocessable Entity: The request was well-formed but was unable to be followed due to semantic errors:  {err.response.headers}")
            elif err.response.status_code == 429:           
                logging.error(f"{err.response.status_code}: Too Many Requests: Exceeded the rate limit:  {err.response.headers}")
                sleep(10)
            elif err.response.status_code == 500:           
                logging.error(f"{err.response.status_code}: Internal Error: Unexpected condition and the server freaked:  {err.response.headers}")
            elif err.response.status_code == 502:           
                logging.error(f"{err.response.status_code}: Bad Gateway: Invalid response from upstream server:  {err.response.headers}")
            elif err.response.status_code == 503:           
                logging.error(f"{err.response.status_code}: Service Unavailable: server overload or down for maintenance:  {err.response.headers}")  
            else:
                logging.error(f"{err.response.status_code}: Unhandled Exception: don't know what to do:  {err.response.headers}")

def main():
    # This is not really needed but is here to help me test and because I am lazy.
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.debug('Start of program')
    
    KEY_FILE = "D:\Development\.keys\gaspars_keys.json"
    CODES_FILE = "gaspars_codes.json"

    with open(KEY_FILE) as f:
        keys = json.load(f)

    store_data = {
                'account_id': keys["account_id"],
                'codes_path': 'D:\\Development\\.keys\\'
                }

    credentials = {
                'client_id': keys["client_id"],
                'client_secret': keys["client_secret"]
                }

    # Creates the connection to lightspeed, and returns a connection object with useful properties
    
    lsr = Connection(store_data, credentials, codes_file=CODES_FILE)
    # items = lsr.get("Category")
    # print(items)

    # data = {"ean": None}
    # lsr.update("Item",7,data)

   # resource = lsr.list('Category',filter="load_relations=all", flatten=True)

    lsr.get("Item", rid=3)




if __name__ == "__main__":
    main()        
