import requests
from requests.exceptions import HTTPError, Timeout

import json
import logging
from time import sleep



class Connection:
    r"""Base class to setup connections and access other objects

    :param store_data: Dictionary with account_id
    :param credentials: Dictionary with client_id, client_secret, and code
    :return: :class:`connection <connection>` object

    """
    def __init__(self, store_data, credentials):
                
        # Because refresh tokens don't expire quickly, we save them locally so we can grab them again later.
        CODES_FILE = 'codes.json'
        
        logging.debug(f"Creating new Lightspeed Connection to account_id : {store_data['account_id']}")
        
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
        self.client_id = credentials['client_id']
        self.client_secret = credentials['client_secret']
        self.api_url = f"https://api.lightspeedapp.com/API/Account/{store_data['account_id']}/"
        self.access_token_url = "https://cloud.lightspeedapp.com/oauth/access_token.php"
        self.access_token = ''  
        self.expires_in = '' 


        # On initiation, the object checks to see if there are codes (access_token and refresh_token) saved locally. If it finds them, it reads them, assigns them to 
        # properties, refreshes them if needed, and returns
        # 1. Check to see if there is a credentials.json already
        try:
            with open(f"{self.save_path}{CODES_FILE}",'r') as f:
                codes = json.load(f)
                # Your refresh token does not expire, so it is actually the important one.
                logging.debug(f"Found codes.json with refresh_token : {codes['refresh_token']}")
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
            logging.debug("Got new codes, which are: %s" % (codes)) 

            # Save the codes in a file on the local system so we can get them (and refresh them) next time  
            with open(f"{self.save_path}{CODES_FILE}", 'w') as outfile:  
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

            logging.debug("Writing out new refreshed codes which are now: %s" % (codes))
            # The data returned in a refresh doesn't include the refresh_token, and we need to update the codes.json file, so rebuild it and write it out to the file
            # TODO - Need to look up the way to append to a dictionary - probably don't need to rebuild the whole thing
            new_codes = {
                    "access_token": codes['access_token'],
                    "expires_in": codes['expires_in'],
                    "token_type": codes['token_type'],
                    "scope": codes['scope'],
                    "refresh_token": self.refresh_token
                    }
            with open(f"{self.save_path}{CODES_FILE}", 'w') as outfile:  
                json.dump(new_codes, outfile, indent=4)

            
            # Now we have nice, fresh codes we can buld the headers property that the API will use
            self.headers = {'authorization' : f'Bearer {self.access_token}'}
            logging.debug(f"Headers are now : {self.headers}")

    def list(self, resource, offset = 0, limit = 100):
        querystring = {'offset':offset, 'limit':limit}
        try:
            lightspeed_api = requests.get(self.api_url + resource + '.json', params=querystring, headers=self.headers)
            logging.debug(f"Request Status Code: {lightspeed_api.status_code}")
            # And hold just the json returned in all_data
            all_data = lightspeed_api.json()

            #Take a look at the header, and get some variables we can use
            logging.debug(lightspeed_api.headers)
            api_drip_rate = float(lightspeed_api.headers['X-LS-API-Drip-Rate'])
            # Since the bucket level comes back as a fraction, we pull it appart to get the pieces we need
            api_bucket_level, api_bucket_size = [(float(x)) for x in lightspeed_api.headers['X-LS-API-Bucket-Level'].split('/')]

            logging.debug(f"Bucket is at {api_bucket_level} with a size of {api_bucket_size} and a current drip rate of {api_drip_rate}")

            # Lightspeed API always returns two top level results in the json - the @attributes which includes count, offset, and limit, 
            # and a second block that actually has the thing from the API. 
            attributes = all_data['@attributes']
            all_resources = []
            all_resources = all_data[resource]

            # We can get the total number of things that are returned from the [@attributes][count]
            total_amount = int(all_data['@attributes']['count']) # We need to use these as integers so we can loop, so convert them
            current_offset = int(all_data['@attributes']['offset']) + int(all_data['@attributes']['limit'])
            current_limit = int(all_data['@attributes']['limit'])
            
            #Loop through the resources to build the full list
            while total_amount > current_offset:
                querystring = {'offset':current_offset, 'limit':current_limit}
                all_data = requests.get(self.api_url + resource + '.json', params=querystring, headers=self.headers).json()
                all_resources.extend(all_data[resource])
                current_offset = current_offset + current_limit

                api_bucket_level, api_bucket_size = [(float(x)) for x in lightspeed_api.headers['X-LS-API-Bucket-Level'].split('/')]
                logging.debug(f"Bucket is at {api_bucket_level} with a size of {api_bucket_size} and a current drip rate of {api_drip_rate}")
        
        except r.exceptions.HTTPError:           
            logging.debug(f"Incorrect Authentication: {r.headers}")
        except requests.exceptions.Timeout:
            logging.debug(f"Timed Out: {r.headers}")
        except requests.exceptions.RequestException as err:
            if err == '422':
                logging.debug(f"Exceeded bucket size - waiting: {r.headers}")
                sleep(10)
            else:
                logging.debug(f"Something went wrong: {err} on headers: {r.headers}")
        
        return all_resources #lightspeed_api.json()



def main():
    # Start logging
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
                'client_id': keys["client_id"],
                'client_secret': keys["client_secret"]
                }

    # Creates the connection to lightspeed, and returns a connection object with useful properties
    lsr = Connection(store_data, credentials)
    items = lsr.list("Category")
    print(items)


if __name__ == "__main__":
    main()        