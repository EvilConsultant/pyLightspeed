from lsretail import LSRetailAPI
import logging
import os # If you are using environment variables for your keys, you need this
import json # If you are using a key file, you need this


# Start logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.debug('Start of program')

# It is recommended that tokens are held as environment variables, not stored in code. Here, Lightspeed key and secret is stored
# as environment variables and retrieved. See https://slack.dev/python-slackclient/auth.html for some additional info on 
# manageing OAuth in Python. Account_ID is the ID of your store. For testing, you could always paste in your info.
client_id = os.environ["LIGHTSPEED_CLIENT_ID"]
client_secret = os.environ["LIGHTSPEED_CLIENT_SECRET"]
account_id = os.environ["LIGHTSPEED_ACCOUNT_ID"]

store_data = {
            'account_id': os.environ["LIGHTSPEED_ACCOUNT_ID"],
            'save_path': 'D:\\Development\\.exports\\'           
            }

credentials = {
            'client_id': os.environ["LIGHTSPEED_CLIENT_ID"],
            'client_secret': os.environ["LIGHTSPEED_CLIENT_SECRET"],
            'credentials_path': 'D:\\Development\\.keys\\codes.json'
            }


# However you do it, you need to handle your keys in a way you like, and you need to get them over to the lsretail object in a dictionary
# that looks like this. You can also stick them in a json file and get them from there if you like.

# KEY_FILE = "D:\Development\.keys\lightspeed_keys.json"

# with open(KEY_FILE) as f:
#     keys = json.load(f)

# store_data = {
#             'account_id': keys["account_id"],
#             'save_path': 'D:\\Development\\.exports\\'
#             }

# credentials = {
#             'client_id': keys["client_id"],
#             'client_secret': keys["client_secret"]
#             'credentials_path': 'D:\\Development\\.keys\\codes.json'
#             }

# Creates the connection to lightspeed, and returns a connection object with useful properties
lsr = LSRetailAPI(store_data, credentials)


