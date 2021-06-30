 
 ## This is a piece of a script that helps process data from wine.com and put it into a database table.
 
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

