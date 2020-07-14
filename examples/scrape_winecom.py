# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import requests
import os
import json
import sys
from bs4 import BeautifulSoup
from urllib.parse import urlparse

import mysql.connector


# %%
sys.path.append('D:\Development\Repositories\pyLightspeed')
print(sys.path)

from lsretail import api as lsretail
from lsecom import api as lsecom

# %%

#establishing the connection
# # conn = mysql.connector.connect(
# #    user='jamie', password='W!neL0ver', host='127.0.0.1', database='vintagewine')

# #Creating a cursor object using the cursor() method
# cursor = conn.cursor()


# %%
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


# %%
lsr = lsretail.Connection(store_data, credentials)

# %%
def process_image(url, image_path, filename, item_id, description = "Image", ordering = 0):
    lsr._manage_rate()
    with open(image_path+filename, "wb") as f:
        f.write(requests.get(url).content)
    url = lsr.api_url+'Image.json'
    
    files = {'image': (filename, open(image_path + filename, 'rb'), 'image/jpeg')}
    payload = {'data': '{"description": "' + description + '", "ordering": ' + ordering +', "itemID": ' + item_id +'}'}
    r = requests.post(url, files=files, data=payload, headers=lsr.headers)
    print(r.text)
# %%
page_link = ""
while page_link != "quit":
    print("Wine.com URL?")
    page_link = input()
    if page_link =="quit": break

    print("Item ID from the LS URL?")
    item_id = input()
    print("System ID?")
    system_id = input()
    # page_link = 'https://www.wine.com/product/ridge-pagani-ranch-zinfandel-2016/510360'
    # item_id = '994'
    # system_id = '210000000998'

    image_path = 'D:\\Data\\CloudStation\\Vintage\\ECommerce\\Graphics\\Products\\'
    # this is the url that we've already determined is safe and legal to scrape from.
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36'}


    # %%

    page_response = requests.get(page_link, headers=headers, timeout=5)
    # here, we fetch the content from the url, using the requests library
    page_content = BeautifulSoup(page_response.content, "html.parser")
    #we use the html parser to parse the url content and store it in a variable.
    textContent = []

    # %% [markdown]
    # # Do the Images
    # Gets the wine images off the page, catches all the information, stores it, and puts the image in Lightspeed via API

    # %%
    # images=page_content.select('body > div.corePage.winePage > main > section.pipMainContent > div.pipHero.prodImageZoom.js-thumbs-enabled > div.pipHero_wrapper > div > picture > img')
    # images = page_content.get('img')
    images = page_content.find_all(class_='pipThumb_image')
    images


    # %%
    for image in images:
        # urlparse will take the url from the image link...
        a = urlparse(image.get('src'))
        # Then we split out the filename and the extension
        (sourcefilename, ext) = os.path.splitext(os.path.basename(a.path))
        link = 'https://www.wine.com/product/images/'+ os.path.basename(a.path)
        ordering = "0"

        if "Bottle" in image.get('alt'):
            filename = system_id + '_btl'+ ext
            ordering = "1"
        elif "Label" in image.get('alt'):
            filename = system_id + '_lbl'+ ext
            ordering = "2"    
        else:
            filename = system_id + sourcefilename + ext
        process_image(link, image_path, filename, item_id, description = image.get('alt'), ordering = ordering)
        print(f"This is {image.get('alt')} from {a.path} saved as {filename}")
    




