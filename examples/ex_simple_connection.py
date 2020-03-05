from retail import connection
import logging
import os
import requests
import json
import pandas

# Start logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.debug('Start of program')

# It is recommended that tokens are held as environment variables, not stored in code. Here, Lightspeed key and secret is stored
# as environment variables and retrieved. See https://slack.dev/python-slackclient/auth.html for some additional info on 
# manageing OAuth in Python. Account_ID is the ID of your store. For testing, you could always paste in your info.
client_id = os.environ["LIGHTSPEED_CLIENT_ID"]
client_secret = os.environ["LIGHTSPEED_CLIENT_SECRET"]
account_id = os.environ["LIGHTSPEED_ACCOUNT_ID"]

# Store Data is passed to the connection() class as a dictionary. Right now, it only has account_id and a local path to store
# refresh keys
store_data = {
            'account_id': os.environ["LIGHTSPEED_ACCOUNT_ID"],
            'save_path': 'D:\\Development\\.keys\\'
            }

credentials = {
            'client_id': os.environ["LIGHTSPEED_CLIENT_ID"],
            'client_secret': os.environ["LIGHTSPEED_CLIENT_SECRET"]
            }

# Creates the connection to lightspeed, and returns a connection object with useful properties
lsr = connection(store_data, credentials)

#Use it to get something
url = lsr.api_url+'Item.json'

r = requests.get(url, headers=lsr.headers)
print(r.json())
df = pandas.read_json(r.json())

