import logging
import requests
import json
import os
import sys
sys.path.append('D:\Development\Repositories\pyLightspeed')
print(sys.path)

from lsretail import api as lsretail
from lsecom import api as lsecom

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
            'client_secret': keys["client_secret"],
            'api_key': keys["api_key"],
            'api_secret': keys["api_secret"]
            }

lsr = lsretail.Connection(store_data, credentials)

# Update all Customers in Lightspeed to show communications are OK. 
customers = lsr.list('Customer', filter = "&load_relations=['Contact']&Contact.noEmail=true")
data = {'Contact':{'noEmail': 'false','noPhone':'false','noMail':'false'}}

for customer in customers:
    lsr.update('Customer', customer['customerID'], data)
    logging.debug(f"Updated {customer['customerID']} {customer['firstName']} {customer['lastName']}")


# Update all eCom customers to activate their email subscription.
lse = lsecom.Connection(store_data, credentials)

customers = lse.list("customers")
subscriptions = lse.list("subscriptions")
for customer in customers:
    # We are looking for matches
    match = False
    # Look at each subscriber and see if they are the customer
    for subscriber in subscriptions:
        if subscriber['email'] == customer['email']:
            #if they are, we have a match
            match = True
    # If there isn't a match, we need to subscribe them
    if match == False:    
        logging.debug(f"Subscribing {customer['firstname']} {customer['lastname']} {customer['email']}")
        data = {
                "subscription": {
                    "isConfirmed": True,
                    "email": customer['email'],
                    "firstname": customer['firstname'],
                    "lastname": customer['lastname'],
                    "doNotifyConfirmed": False,
                    "language": "US"
                    }
                }
        lse.create("subscriptions", data)
#
# ITEM UPDATES
#
#Update all items that don't have a customSku so they get copied to ecom
data = {}
items = lsr.list('Item', filter = 'customSku=~,')

for item in items:
    data = {'customSku': item['systemSku']}
    lsr.update('Item', item['itemID'], data)
    logging.debug(f"Updated {item['itemID']} {item['description']}")