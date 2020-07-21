
class LSRetailAPI(object):
    r"""Base class to setup connections and access other objects

    :param store_data: Dictionary with account_id and save_path
    :param credentials: Dictionary with client_id, client_secret, and path for storing temporary codes
    :return: :class:`connection <connection>` object
    """

    def __init__(self, store_data=None, credentials=None):
        
        logging.debug(f"Creating new Lightspeed Connection to account_id : {store_data['account_id']}")
        self.account_id = store_data['account_id']
        self.save_path = store_data['save_path']
        self.client_id = credentials['client_id']
        self.client_secret = credentials['client_secret']
        self.api_url = f"https://api.lightspeedapp.com/API/Account/{store_data['account_id']}/"
        self.access_token_url = "https://cloud.lightspeedapp.com/oauth/access_token.php"
        self.access_token = ''  
        self.expires_in = '' 

        self.refresh_connection(self, store_data, credentials)    

    def refresh_connection(self, store_data, credentials):
        """
        Refreshes the connection and makes sure the access keys are updated
        """
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

    








def main():
    return

if __name__ == "__main__":
    main()      