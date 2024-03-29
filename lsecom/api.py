<<<<<<< HEAD
import requests
from requests.exceptions import HTTPError, Timeout

import json
import logging
from time import sleep
import time
import pandas as pd


class Connection:
    r"""LS Ecomm Base Class

    """
    def __init__(self, store_data, credentials, codes_file):
                
        # Because refresh tokens don't expire quickly, we save them locally so we can grab them again later.
        self.codes_file = codes_file
        
        logging.info(f"LSECOM_API: Creating new Lightspeed Connection with {codes_file} (Store: {store_data['account_id']})")
        
        # A reminder on how Lightspeed tokens work:
        # Temporary token (CODE) - A temp token generated when a user authenticates to lightspeed. It is returned in the URL as code= and called code when passed to the lightspeed api
        # Refresh token (refresh_token) - Does not expire and should be saved (you can also see them in the Lightspeed UI under Settings > Client API Access > API Client
        #                                 The refresh_token is used to get a new, fresh access_token
        # Access token (access_token) - Used to actually get info from the API. Access tokens expire (expires_in) and need to be checked and periodically refreshed by
        #                               using the refresh_token
        # So you first have a user authenticate with their username and password which gives you CODE, you use CODE to get a new refresh_token and access_token, and you use
        # the refresh_token to periodically get new/refresh the access_token, and you use the access_token to actually get things from the API. Whew.

        self.account_id = store_data['account_id']
        self.codes_path = store_data['codes_path']
        self.api_key = credentials['api_key']
        self.api_secret = credentials['api_secret']
        self.client_id = credentials['client_id']
        self.client_secret = credentials['client_secret']
        
        # For vintage the language was en, but gaspars it is us
        self.api_url = f"https://{credentials['api_key']}:{credentials['api_secret']}@{credentials['api_url']}"
        #self.api_url = f"https://{credentials['api_key']}:{credentials['api_secret']}@api.shoplightspeed.com/us/"
        #self.access_token_url = "https://cloud.lightspeedapp.com/oauth/access_token.php"
        #self.access_token = ''  
        #self.expires_in = ''
        self.response = None
        self.request_counter = 0
        #self.refresh_token=""
        #self.timeout = 7.0  # need to catch timeout?
        
        #self.token_refresh()
        self._session = requests.Session()
    
    
    
    def token_refresh(self):
        # On initiation, the object checks to see if there are codes (access_token and refresh_token) saved locally. If it finds them, it reads them, assigns them to 
        # properties, refreshes them if needed, and returns
        # 1. Check to see if there is a credentials.json already
        logging.info(f"REFRESH TOKEN: Trying to refresh token...")
        try:
            with open(f"{self.codes_path}{self.codes_file}",'r') as f:
                codes = json.load(f)
                # Your refresh token does not expire, so it is actually the important one.
                logging.debug(f"REFRESH TOKEN: Found codes.json with refresh_token : {codes['refresh_token']}")
        except FileNotFoundError as err:

            # TODO: Need to add back in the code that checks the environment variables for keys. This should handle both env and file keys
            logging.warning("No Codes File Found:{0}".format(err))
            # 2. If there are no keys, it should fire the process to get a temp token, authenticate the user, and write out the creds
            # For now we are going to do it manually by going to
            # https://cloud.lightspeedapp.com/oauth/authorize.php?response_type=code&client_id={YOUR CLIENT ID}&scope=employee:all
            # to obtain the CODE. Paste that CODE (it is in the URL returned) below and run this before the CODE expires (30 seconds)
            # to get your access token back.
            CODE = "XXXXX" 
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
            with open(f"{self.codes_path}{self.codes_file}", 'w') as outfile:  
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
            self.expires = time.time() + self.expires_in
            logging.debug(f"REFRESH TOKEN: Token refreshed, expires in {self.expires_in} seconds")
            #logging.debug("Writing out new refreshed codes which are now: %s" % (codes))
            # The data returned in a refresh doesn't include the refresh_token, and we need to update the codes.json file, so rebuild it and write it out to the file
            # TODO - Need to look up the way to append to a dictionary - probably don't need to rebuild the whole thing
            new_codes = {
                    "access_token": codes['access_token'],
                    "expires_in": codes['expires_in'],
                    "token_type": codes['token_type'],
                    "scope": codes['scope'],
                    "refresh_token": self.refresh_token
                    }
            with open(f"{self.codes_path}{self.codes_file}", 'w') as outfile:  
                json.dump(new_codes, outfile, indent=4)

            
            # Now we have nice, fresh codes we can buld the headers property that the API will use
            self.headers = {'authorization' : f'Bearer {self.access_token}'}
            logging.debug(f"REFRESH TOKENS: Headers are now : {self.headers}")
    
    def write_out(self, filepath, resource):
        to_json = open(filepath + '.json', 'w')
        to_json.write(json.dumps(resource, indent=4))
        to_json.close()
        pd.DataFrame(resource).to_csv(filepath +'.csv', index=False, encoding='utf-8-sig')
        logging.info(f'Wrote {resource} data to {filepath}')

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
    

    def list(self, resource, filter = "", sublist = "", limit = 250, page = 1, rows = 0):

        if sublist =="": sublist = resource

        response = requests.request('GET', self.api_url + resource + '/count.json')

        #Get the total Count
        total_amount = response.json()["count"]
        current_offset = 0
        all_resources = []
        
        #process the filters from the extremly limited filter options Lightspeed provides
        if filter == "":
            url = self.api_url + resource + '.json'
        else:
            url = self.api_url + resource + '.json?' + filter
        #Loop through based on a limit of 250
        while total_amount > current_offset:
            querystring = {'page':page, 'limit':limit}
            response = requests.get(url, params=querystring)
            response.raise_for_status()
            all_data = response.json()
            all_resources.extend(all_data[sublist])
            current_offset = current_offset + limit
            page = page+1
               
        return all_resources #self.response.json()
    
    def create(self, resource, payload):
        url = self.api_url + resource + '.json'
        self.response = requests.post(url, data=json.dumps(payload))

    def update(self, resource, id, payload):
        try:
            url = self.api_url + resource + "/"+ str(id) + '.json'
            self.response = requests.put(url, data=json.dumps(payload))
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
    pass
   

if __name__ == "__main__":
    main()        
=======
import requests
from requests.exceptions import HTTPError, Timeout

import json
import logging
from time import sleep
import time
import pandas as pd


class Connection:
    r"""LS Ecomm Base Class

    """
    def __init__(self, store_data, credentials):
                
        # Because refresh tokens don't expire quickly, we save them locally so we can grab them again later.
        self.codes_file = 'codes.json'
        
        logging.debug(f"LS ECOM: Creating new Lightspeed Ecom to account_id : {store_data['account_id']}")
        
        # A reminder on how Lightspeed tokens work:
        # Temporary token (CODE) - A temp token generated when a user authenticates to lightspeed. It is returned in the URL as code= and called code when passed to the lightspeed api
        # Refresh token (refresh_token) - Does not expire and should be saved (you can also see them in the Lightspeed UI under Settings > Client API Access > API Client
        #                                 The refresh_token is used to get a new, fresh access_token
        # Access token (access_token) - Used to actually get info from the API. Access tokens expire (expires_in) and need to be checked and periodically refreshed by
        #                               using the refresh_token
        # So you first have a user authenticate with their username and password which gives you CODE, you use CODE to get a new refresh_token and access_token, and you use
        # the refresh_token to periodically get new/refresh the access_token, and you use the access_token to actually get things from the API. Whew.

        self.account_id = store_data['account_id']
        self.save_path = store_data['save_path']
        self.api_key = credentials['api_key']
        self.api_secret = credentials['api_secret']
        self.api_url = f"https://{credentials['api_key']}:{credentials['api_secret']}@api.shoplightspeed.com/en/"
        #self.access_token_url = "https://cloud.lightspeedapp.com/oauth/access_token.php"
        #self.access_token = ''  
        #self.expires_in = ''
        self.response = None
        self.request_counter = 0
        #self.refresh_token=""
        #self.timeout = 7.0  # need to catch timeout?
        
        #self.token_refresh()
        self._session = requests.Session()

    def token_refresh(self):
        # On initiation, the object checks to see if there are codes (access_token and refresh_token) saved locally. If it finds them, it reads them, assigns them to 
        # properties, refreshes them if needed, and returns
        # 1. Check to see if there is a credentials.json already
        logging.info(f"REFRESH TOKEN: Trying to refresh token...")
        try:
            with open(f"{self.save_path}{self.codes_file}",'r') as f:
                codes = json.load(f)
                # Your refresh token does not expire, so it is actually the important one.
                logging.debug(f"REFRESH TOKEN: Found codes.json with refresh_token : {codes['refresh_token']}")
        except FileNotFoundError as err:

            # TODO: Need to add back in the code that checks the environment variables for keys. This should handle both env and file keys
            logging.warning("No Codes File Found:{0}".format(err))
            # 2. If there are no keys, it should fire the process to get a temp token, authenticate the user, and write out the creds
            # For now we are going to do it manually by going to
            # https://cloud.lightspeedapp.com/oauth/authorize.php?response_type=code&client_id={YOUR CLIENT ID}&scope=employee:all
            # to obtain the CODE. Paste that CODE (it is in the URL returned) below and run this before the CODE expires (30 seconds)
            # to get your access token back.
            CODE = "XXXXX" 
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
            with open(f"{self.save_path}{self.codes_file}", 'w') as outfile:  
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
            self.expires = time.time() + self.expires_in
            logging.debug(f"REFRESH TOKEN: Token refreshed, expires in {self.expires_in} seconds")
            #logging.debug("Writing out new refreshed codes which are now: %s" % (codes))
            # The data returned in a refresh doesn't include the refresh_token, and we need to update the codes.json file, so rebuild it and write it out to the file
            # TODO - Need to look up the way to append to a dictionary - probably don't need to rebuild the whole thing
            new_codes = {
                    "access_token": codes['access_token'],
                    "expires_in": codes['expires_in'],
                    "token_type": codes['token_type'],
                    "scope": codes['scope'],
                    "refresh_token": self.refresh_token
                    }
            with open(f"{self.save_path}{self.codes_file}", 'w') as outfile:  
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

    def list(self, resource, filter = "", sublist = "", limit = 250, page = 1, rows = 0):

        if sublist =="": sublist = resource

        response = requests.request('GET', self.api_url + resource + '/count.json')

        #Get the total Count
        total_amount = response.json()["count"]
        current_offset = 0
        all_resources = []
        
        #process the filters from the extremly limited filter options Lightspeed provides
        if filter == "":
            url = self.api_url + resource + '.json'
        else:
            url = self.api_url + resource + '.json?' + filter
        #Loop through based on a limit of 250
        while total_amount > current_offset:
            querystring = {'page':page, 'limit':limit}
            response = requests.get(url, params=querystring)
            response.raise_for_status()
            all_data = response.json()
            all_resources.extend(all_data[sublist])
            current_offset = current_offset + limit
            page = page+1
               
        return all_resources #self.response.json()
    
    def create(self, resource, payload):
        url = self.api_url + resource + '.json'
        self.response = requests.post(url, data=json.dumps(payload))

    def update(self, resource, id, payload):
        try:
            url = self.api_url + resource + "/"+ str(id) + '.json'
            self.response = requests.put(url, data=json.dumps(payload))
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
    def write_out(filepath, resource):
        to_json = open(filepath + '.json', 'w')
        to_json.write(json.dumps(resource, indent=4))
        to_json.close()
        pd.DataFrame(resource).to_csv(filepath +'.csv', index=False, encoding='utf-8-sig')
        logging.debug(f'Wrote data to {filepath}')
    
    # This is not really needed but is here to help me test and because I am lazy.
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.debug('Start of program')
    
    KEY_FILE = "D:\Development\.keys\lightspeed_keys.json"

    with open(KEY_FILE) as f:
        keys = json.load(f)

    store_data = {
                'account_id': keys["account_id"],
                'save_path': 'D:\\Development\\.keys\\'
                }

    credentials = {
                'api_key': keys["api_key"],
                'api_secret': keys["api_secret"]
                }

    # Creates the connection to lightspeed, and returns a connection object with useful properties
    lse = Connection(store_data, credentials)
    
    orders = lse.list("orders", filter="created_at_min=2020-05-10 00:00:00")
    order_products = []
    write_out(lse.save_path + 'ecom_orders', orders)

    for order in orders:
        resource = lse.list('orders/'+ str(order['id'])+'/products', sublist = 'orderProducts')
        order_products.extend(resource)
    
    write_out(lse.save_path + 'ecom_orders_products', order_products)
   

if __name__ == "__main__":
    main()        
>>>>>>> c2cff1f72b3ee02d25ebbb0ea2590fe7c3a5328c
