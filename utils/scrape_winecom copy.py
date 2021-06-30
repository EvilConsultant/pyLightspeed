# To add a new cell, type '# %%'
# To add a new markdown cell, type '# %% [markdown]'
# %%
import requests
import os
import json
import sys
from bs4 import BeautifulSoup
import urllib.parse

import mysql.connector
import re
import math

from selenium import webdriver

# %%
sys.path.append('D:\Development\Repositories\WineFoundry\pyLightspeed')
print(sys.path)

from lsretail import api_dev as lsretail
#from lsecom import api as lsecom

# %%https://www.wine.com/product/chateau-vitallis-pouilly-fuisse-2018/540407

#establishing the connection
conn = mysql.connector.connect(user='jamie', password='W!neL0ver', host='127.0.0.1', database='vintagewine')
#Creating a cursor object using the cursor() method
cursor = conn.cursor()

#And set up the webdriver
driver = webdriver.Chrome('D:\\Development\\chromedriver.exe')
# %%
store_datafile = 'D:\\Development\\.keys\\vintage_keys.json'
lsr = lsretail.Connection(store_datafile)

# %%
def process_image(url, image_path, filename, item_id, description = "Image", ordering = 0):
    lsr._manage_rate()
    with open(image_path+filename, "wb") as f:
        f.write(requests.get(url).content)
    url = lsr.api_url+'Image.json'
    
    files = {'image': (filename, open(image_path + filename, 'rb'), 'image/jpeg')}
    payload = {'data': '{"description": "' + description + '", "ordering": ' + ordering +', "itemID": ' + item_id +'}'}
    r = requests.post(url, files=files, data=payload, headers=lsr.headers)
    #print(r.text)

def round_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.ceil(n * multiplier) / multiplier

# %%
item_id=""
while item_id !="quit":
    item_id = input('Item ID from Lightspeed? : ')
    if item_id =="quit": break

    item = lsr.get("Item", rid=item_id)
    system_id = item["Item"]["systemSku"]

    driver.get(f"http://www.wine.com/search/{urllib.parse.quote(item['Item']['description'])}/0?showOutOfStock=true")

    if input("Have you found the right page? : ") == 'y':
        page_link = driver.current_url
    else:
        continue
 

    image_path = 'D:\\Data\\CloudStation\\Vintage\\ECommerce\\Graphics\\Products\\'
    # this is the url that we've already determined is safe and legal to scrape from.
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36'}


    page_response = requests.get(page_link, headers=headers, timeout=5)
    # here, we fetch the content from the url, using the requests library
    page_content = BeautifulSoup(page_response.content, "html.parser")
    #we use the html parser to parse the url content and store it in a variable.
    textContent = []
    # %%
    # %% [markdown]
    # # Build and Store Webscrape
    # I am storing webscraped data in a webscrape table. This isn't an automated scrape, but I still want to put it in there. Also, since this is manually matched
    # this data can be used in the future to train record matching algos.
    #
    if page_content.find(class_='icon icon-screwcap prodAttr_icon prodAttr_icon-screwcap'):
        closure = 'Screwcap'
    else:
        closure = ''

    if page_content.find(class_='icon icon-glass-red prodAttr_icon prodAttr_icon-redWine'):
        category = 'Red'
    elif page_content.find(class_='icon icon-glass-white prodAttr_icon prodAttr_icon-whiteWine'):
        category = 'White'
    elif page_content.find(class_='icon icon-champagne prodAttr_icon prodAttr_icon-champagne'):
        category = 'Sparkling'
    elif page_content.find(class_='icon icon-glass-white prodAttr_icon prodAttr_icon-roseWine'):
        category = 'Rose'
    else:
        category = ''

    try:
        price = float(re.findall('[0-9.]+', page_content.find(class_='productPrice').text)[0].strip())
    except AttributeError:
        price = 0
    
    try:
        msrp = round_up(float(re.findall('[0-9.]+', page_content.find(class_='productPrice_price-regWhole').text)[0].strip()))
    except AttributeError:
        msrp = price

    try:
        vintage = re.findall('[0-9]+', page_content.find(class_='pipName').text)[0].strip()
    except IndexError:
        vintage = 0

    # %%
    insert_webscrape = ("INSERT INTO webscrapes "
                        "(retail_systemID, is_match, best_match, _web_scraper_order, web_scraper_start_url, scrape_sourceID, sku, product, product_href, title, name, vintage, producer, brand, price, msrp, region, subregion, description, size, alcohol, closure, category, varietal) "
                        "VALUES (%(retail_systemID)s, %(is_match)s, %(best_match)s, %(_web_scraper_order)s, %(web_scraper_start_url)s, %(scrape_sourceID)s, %(sku)s, %(product)s, %(product_href)s, %(title)s, %(name)s, %(vintage)s, %(producer)s, %(brand)s, %(price)s, %(msrp)s, %(region)s, %(subregion)s, %(description)s, %(size)s, %(alcohol)s, %(closure)s, %(category)s, %(varietal)s)")

    data = {
        'retail_systemID': system_id,
        'is_match': 1,
        'best_match': 1,
        '_web_scraper_order': system_id,
        'web_scraper_start_url': page_link,
        'scrape_sourceID': 7,
        'sku':  page_content.find(attrs={'name':'productID'})["content"],
        'product': page_content.find(class_='pipName').text,
        'product_href': page_link,
        'title': page_content.find(class_='pipName').text,
        'name':  re.findall('[A-z ]+', page_content.find(class_='pipName').text)[0].strip(),
        'vintage': vintage,
        'producer': page_content.find(class_='pipWinery_headlineLink').text,
        'brand': page_content.find(class_='pipWinery_headlineLink').text,
        'price': price,
        'msrp': msrp,
        'region': page_content.find(attrs={'name':'productVarietal'})["content"],
        'subregion':  page_content.find(attrs={'name':'productRegion'})["content"],
        'description':  page_content.find(class_='viewMoreModule_text').text,
        'size': page_content.find(class_='prodAlcoholVolume_text').text,
        'alcohol': page_content.find(class_='prodAlcoholPercent_percent').text,
        'closure':  closure,
        'category': category,
        'varietal': page_content.find(attrs={'name':'productVarietal'})["content"]  
    }

    cursor.execute(insert_webscrape, data)
    conn.commit()

    # %% [markdown]
    # ## Store Reviews and Build Description
    # 
    # We store reviews in the Reviews table, and use them to create an HTML description to post.

    # %%
    # Start the description so we can append reviews if any
    item_content =""
    item_content = '<p>' + page_content.find(class_='viewMoreModule_text').text

    reviews = page_content.select('div.pipProfessionalReviews_list')
    # If there are reviews, add a header to the content
    if reviews:
        item_content = item_content + '</p><p><strong>Tasting Notes</strong></p>'
    else:
        item_content = item_content + '</p>'

    for review in reviews:
        # Writing the HTML is failing, I am sure because I need to escape some things, but it isn't really needed so I am skipping it.
        insert_review = ("INSERT INTO wine_reviews "
                    "(source, initials, rating, review_detail, wine_itemID, wine_systemSKU, url) "
                    "VALUES (%(source)s, %(initials)s, %(rating)s, %(review_detail)s, %(wine_itemID)s, %(wine_systemSKU)s, %(url)s)")
        data = {
            'source': review.select('div[class="pipProfessionalReviews_authorName"]')[0].text,
            'initials': review.select('span[class="wineRatings_initials"]')[0].text,
            'rating': int(review.select('span[class="wineRatings_rating"]')[0].text),
            'review_detail': review.select('div[class="pipProfessionalReviews_review"]')[0].text,
            'wine_itemID': int(item_id),
            'wine_systemSKU': system_id,
            'url': page_link
            
        }
        item_content = item_content + "<p><emphasis>" + review.select('span[class="wineRatings_rating"]')[0].text + " " + review.select('div[class="pipProfessionalReviews_authorName"]')[0].text + "</emphasis><br />"
        item_content = item_content + review.select('div[class="pipProfessionalReviews_review"]')[0].text + "</p>"
        cursor.execute(insert_review, data)
        conn.commit()


    
    # %%
    # ## Build the data that gets pushed in to Lightspeed

   
    #item_content = '<p>' + page_content.find(class_='pipWineNotes_copy viewMoreModule').text + '</p><h3>Tasting Notes</h3>'
    # 
    # If it got a good score, we want to hightlight it"
    if reviews and int(review.select('span[class="wineRatings_rating"]')[0].text) >= 90:
        item_description = reviews[0].select('span[class="wineRatings_rating"]')[0].text + "pts. " + page_content.find(class_='viewMoreModule_text').text[:100]+"..."
    else:
        item_description = page_content.find(class_='viewMoreModule_text').text[:112]+"..."

    # ## Write what little we can to Lightspeed
    # Lightspeed won't let you write directly to Product in eCom for things that are omni, so we have to make sure they are not active for eCom in Retail, then write using the retail api, then activate them for eCom.

    # %%
#"publishToEcom": True,
    data = {"publishToEcom": True,
            "Prices":{
                "ItemPrice":{
                    "amount": msrp,
                    "useType":"MSRP",
                    "useTypeID": 2
                    }
                },
            "ItemECommerce":{
                "shortDescription":item_description,
                "longDescription": item_content,
                "weight": 48        
                }
            }
    
    lsr.update("Item", item_id, data)

    # %% [markdown]
    # # Do the Images
    # Gets the wine images off the page, catches all the information, stores it, and puts the image in Lightspeed via API

    # %%
    images = page_content.find_all(class_='pipThumb_image')
    for image in images:
        # urlparse will take the url from the image link...
        a = urllib.parse.urlparse(image.get('src'))
        # Then we split out the filename and the extension
        (sourcefilename, ext) = os.path.splitext(os.path.basename(a.path))
        link = 'https://www.wine.com/product/images/'+ os.path.basename(a.path)
        ordering = "0"

        if "Bottle" in image.get('alt'):
            if "Front" in image.get('alt'):
                filename = system_id + '_btl'+ ext
                ordering = "1"
            elif "Back" in image.get('alt'):
                filename = system_id + '_btlb'+ ext
                ordering = "3"
            else:
                filename = system_id + '_btl_'+ sourcefilename + ext
                ordering = "5"
        elif "Label" in image.get('alt'):
            if "Front" in image.get('alt'):
                filename = system_id + '_lbl'+ ext
                ordering = "2"
            elif "Back" in image.get('alt'):
                filename = system_id + '_lblb'+ ext
                ordering = "4"
            else:
                filename = system_id + '_lbl_'+ sourcefilename + ext
                ordering = "6"
        else:
            filename = system_id + sourcefilename + ext
        process_image(link, image_path, filename, item_id, description = image.get('alt'), ordering = ordering)
        print(f"This is {image.get('alt')} from {a.path} saved as {filename}")
   
driver.close() 


