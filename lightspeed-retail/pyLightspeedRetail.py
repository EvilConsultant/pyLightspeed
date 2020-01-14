import requests
import json
import os
import logging


class LightspeedRetail:
    r"""Base class to setup connections and access other objects

    :param store_data: Dictionary with account_id
    :param credentials: Dictionary with client_id, client_secret, and code
    :return: :class:`LightspeedRetail <LightspeedRetail>` object

    """
    def __init__(self, store_data, credentials):
                
        # self.token_type = store_data['token_type']
        # self.scope = store_data['scope']
        # self.refresh_token = store_data['refresh_token']
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

            # MORE TEST AND FIX HERE, THIS ISNT WORKING YET
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
             # If there are codes, get them out of the json file and set the class properties
            self.access_token = codes['access_token']
            self.token_type = codes['token_type']
            self.scope = codes['scope']
            self.refresh_token = codes['refresh_token']
            # Check to see if the access_token is still working, and if not, refresh it
            # TODO - For now, I am forcing a refresh. Need to come back and write some checking
            payload = {
                'refresh_token': self.refresh_token,
                'client_secret': self.client_secret,
                'client_id': self.client_id,
                'grant_type': 'refresh_token',
            }
            r = requests.post(self.access_token_url, data=payload)
            codes = r.json()
            logging.debug("Writing out new refreshed codes which are now: %s" % (codes))
            # The data returned in a refresh doesn't include the refresh_token, and we need to update the codes.json file, so rebuild it and write it out to the file
            # TODO - Need to look up the way to append to a dictionary - probably don't need to rebuild the whole thing
            codes = {
                    "access_token": codes['access_token'],
                    "expires_in": codes['expires_in'],
                    "token_type": codes['token_type'],
                    "scope": codes['scope'],
                    "refresh_token": self.refresh_token
                    }
            with open(f"{self.save_path}2{CODES_FILE}", 'w') as outfile:  
                json.dump(codes, outfile, indent=4)

            self.expires_in = codes['expires_in']
            # Now we have nice, fresh codes we can buld the headers property that the API will use
            self.headers = 'Bearer {'+ codes["access_token"] + '}'
            logging.debug(f"Headers are now : {self.headers}")

    def list(self, url):
        logging.debug(f"List: {url}")
        r = requests.get(self.api_url + url + '.json', headers=self.headers)
        return r.json()

def main():
    # Start logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.debug('Start of program')

    # It is recommended that tokens are held as environment variables, not stored in code. Here, Lightspeed key and secret is stored
    # as environment variables and retrieved. See https://slack.dev/python-slackclient/auth.html for some additional info on 
    # manageing OAuth in Python. Account_ID is the ID of your store. For testing, you could always paste in your info.
    client_id = os.environ["LIGHTSPEED_CLIENT_ID"]
    client_secret = os.environ["LIGHTSPEED_CLIENT_SECRET"]
    account_id = os.environ["LIGHTSPEED_ACCOUNT_ID"]
  

    # temp_token is the Temp token copied and pasted from the return of this link, need to come back to this
    # URL use to authenticate user: https://cloud.lightspeedapp.com/oauth/authorize.php?response_type=code&client_id=XXXX&scope=employee:all
    temp_token = 'XXXXXX'

    # Store Data is passed to the LightspeedRetail() class as a dictionary. Right now, it only has account_id, but we may
    # need more in the future
    store_data = {
                'account_id': account_id,
                'save_path': 'D:\\Development\\.keys\\'
                }
    # Credential is passed to LightspeedRetail() and includes the keys. It includes CODE now while developing until I can
    # build it in to the __init__
    credentials = {
                'client_id': client_id,
                'client_secret': client_secret
                 }


    lsr = LightspeedRetail(store_data, credentials)
    print(lsr.List('Item'))


if __name__ == "__main__":
    main()        