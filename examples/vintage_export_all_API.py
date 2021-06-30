# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %% [markdown]
# # Export Data via API for Import to Database
# 
# This exports all the major data from Lightspeed POS to spreadsheets. This is helpful if you need to migrate off lightspeed, or you just want backups of all the major things

# %%
import logging
import requests
import json
import pandas as pd
import sys
sys.path.append('D:\Development\Repositories\pyLightspeed')
# Start logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.debug('Start of program')

# %% [markdown]
# ## Import the Module
# Make sure your environment paths are set correctly if you are getting module not found errors.

# %%
from lsretail import api
from lsecom import api as lsecom

# %% [markdown]
# ## Get Keys
# This example uses a file you will have to create on your local machine to store keys. This is not best practice - you should probably store your keys in environment variables - but is simpler for people just trying to test and play. See the example files in example\data and adjust with your information.

# %%
KEY_FILE = "D:\\Development\\.keys\\vintage_keys.json"
CODES_FILE = "vintage_codes.json"

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
            'api_secret': keys["api_secret"],
            'api_url': keys["api_url"]
            }

# %% [markdown]
# ## Create a Connection
# Call the connection class, which will return an active connection to Lightspeed.

# %%
def write_out(filepath, resource):
    to_json = open(filepath + '.json', 'w')
    to_json.write(json.dumps(resource, indent=4))
    to_json.close()
    pd.DataFrame(resource).to_csv(filepath +'.csv', index=False, encoding='utf-8-sig')
    logging.debug(f'Wrote data to {filepath}')


# %%
# Creates the connection to lightspeed, and returns a connection object with useful properties

lsr = api.Connection(store_data, credentials, codes_file = CODES_FILE)


#Where do you want to save the files?
EXPORT_PATH = "D:\\Data\\CloudStation\\Vintage\\ETLs\\API Exports\\"

# %% [markdown]
# ## Export things
# 
# This takes a tuple of API endpoints (make sure they are spelled right) and loops through them, dumping the results to a .csn and raw JSON file

# %%
#Get a list of things

#exports = ('Manufacturer','Category','Employee', 'Register','CustomerType','TaxCategory')
#exports = ('Manufacturer','Category','Vendor')
exports = ('Sale', 'SaleLine','CustomerType','Manufacturer','Vendor', 'Order', 'OrderLine','Category', 'Employee', 'Register', 'Image')
#exports = ('Image', 'Register')
#These are updated rarely, so likely don't need to run them, but here if you want to refresh
#exports = ('Category','Employee', 'Register','CustomerType','TaxCategory' )


for export in exports:
    resource = lsr.list(export, filter='archived=true')
    write_out(EXPORT_PATH + export, resource)

# %% [markdown]
# ### Customers are Special
# For Customers we want to load with the Contact area

# %%
# customers = lsr.list("Customer", filter = 'load_relations=["Contact"]&archived=true')
# write_out(EXPORT_PATH + 'Customer_Contact', customers)


# %%
# Items are Special
# We need to get some Quantity on Hand information, so we need to include the relationship.
# items = lsr.list("Item", filter = 'load_relations=["ItemShops","Images"]&archived=true')
# write_out(EXPORT_PATH + 'Item_Shop', items)

# %% [markdown]
# # Export eCom transactions

# %%
#Get a list of things

#exports = ('products', 'variants', 'tags')

exports = ('orders', 'customers', 'products', 'variants', 'filters', 'tags','discounts')
# #exports = ('orders', 'customers', 'products')

# lse = lsecom.Connection(store_data, credentials, codes_file = CODES_FILE)
# for export in exports:
#     resource = lse.list(export)
#     write_out(EXPORT_PATH + 'ecom_' + export, resource)
 
