# used to handle the keys file
import json

# Depending on where you downloaded this, the module is probably not being found by python. This adds the parent directory to the path so the import works.
import sys
sys.path.append('../')
print(sys.path)

#imports the api code. If this fails, you probably have your path wrong.
from pyLightspeed.lsretail import api


# Get the keys file
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

#Creates a connection
lsr = api.Connection(store_data, credentials)

#Gets a list of Categories. Pass the name of the API
categories = lsr.list("Category")

print(categories)