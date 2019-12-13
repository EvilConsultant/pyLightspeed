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
                
        self.access_token = ''  
        self.expires_in = '' 
        self.token_type = store_data['token_type']
        self.scope = store_data['scope']
        self.refresh_token = store_data['refresh_token']
        self.account_id = store_data['account_id']
        self.client_id = credentials['client_id']
        self.client_secret = credentials['client_secret']
        self.api_url = 'https://api.lightspeedapp.com/API/Account/'
        self.access_token_url = 'https://cloud.lightspeedapp.com/oauth/access_token.php'

        # A new object should:
        # 1. Check to see if there is a credentials.json already
        # 2. If there are no keys, it should fire the process to get a temp token, authenticate the user, and write out the creds
        # 3. If there are keys, it should get them out of the Json and update the properties
        # 4. It should force_refresh the keys
        # 3. Make
    def force_refresh(self):
        payload = {
            'refresh_token': f'{self.refresh_token}',
            'client_secret': f'{self.client_secret}',
            'client_id': f'{self.client_id}',
            'grant_type': 'refresh_token',
        }
        r = requests.request("POST",
                             'https://cloud.lightspeedapp.com/oauth/access_token.php',
                             data=payload).json()
        self.access_token = r['access_token']
        self.expires_in = r['expires_in']



def main():
    # Start logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.debug('Start of program')

    # It is recommended that tokens are held as environment variables, not stored in code. Here, Lightspeed key and secret is stored
    # as environment variables and retrieved. See https://slack.dev/python-slackclient/auth.html for some additional info on 
    # manageing OAuth in Python. Account_ID is the ID of your store. For testing, you could always paste in your info.
    client_id = os.environ["LIGHTSPEED_CLIENT_ID"]
    client_secret = os.environ["LIGHTSPEED_CLIENT_SECRET"]
    client_secret = os.environ["LIGHTSPEED_ACCOUNT_ID"]
    ACCOUNT_ID = "190211"

    # temp_token is the Temp token copied and pasted from the return of this link, need to come back to this
    # URL use to authenticate user: https://cloud.lightspeedapp.com/oauth/authorize.php?response_type=code&client_id=577f37979925d3afa87ae7c870c34c126b856f8e6297acddb7a753a6fe005e74&scope=employee:all
    temp_token = '6c3ed4eb5944f6d1b126061ce5dcf45eb2513758'

    # Store Data is passed to the LightspeedRetail() class as a dictionary. Right now, it only has account_id, but we may
    # need more in the future
    store_data = {
                'account_id': ACCOUNT_ID
                }
    # Credential is passed to LightspeedRetail() and includes the keys. It includes CODE now while developing until I can
    # build it in to the __init__
    credentials = {
                'client_id': client_id,
                'client_secret': client_secret
                 }


    lsr = LightspeedRetail(store_data, credentials)

    r = requests.post(url, data=payload)
    #Logs credentials to the virtual console
    access_token = r.json()
    print(json.dumps(credentials, indent=4))
    print(list(credentials.keys()))



    # creates credentials file with json response  
    with open('D:\Development\.keys\credentials.json', 'w') as outfile:  
        json.dump(credentials, outfile, indent=4)

if __name__ == "__main__":
    main()        