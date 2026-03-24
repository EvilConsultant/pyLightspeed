# Starting to convert the mightly updates to the new api wrapper
# but I will need to create the customer and contact wrapper first

#This is all because this is in the utils directory
import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.debug('Start of program')


logging.debug(sys.path)

import api
import store


KEY_FILE = "D:\\Development\\.keys\\vi..._keys.json"
my_store = store.LightspeedStore(KEY_FILE)

lsretail = api.LightspeedApi(client_id=my_store.client_id, client_secret=my_store.client_secret, store_hash=my_store.account_id, access_token=my_store.access_token, token_file = my_store.token_file, host=my_store.retail_api_host, rate_limiting_management = {'min_requests_remaining':2, 'wait':True, 'callback_function':None})
lsecom = api.LightspeedApi(host=my_store.ecom_api_host, basic_auth=(my_store.api_key, my_store.api_secret))

# Update all Customers in Lightspeed to show communications are OK. 

customers = lsretail.Customers.all(filter = r'load_relations=%5B%22Contact%22%5D&Contact.noEmail=true')
data = {'Contact':{'noEmail': 'false','noPhone':'false','noMail':'false'}}

for customer in customers:
    customer.update(data)
    logging.debug(f"Updated {customer.customerID} {customer.firstName} {customer.lastName}")   
