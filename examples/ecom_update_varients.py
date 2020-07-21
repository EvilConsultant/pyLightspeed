lse = Connection(store_data, credentials)


varients = lse.list("variants")

for varient in varients:
    data = {}
    if varient["weight"] == 0 :
        data = '''{
                "variant": {
                    "weightValue": 48.0,
                    "weightUnit": "oz",
                    }
                }'''


    lse.update("variants", varient["id"], data)
    logging.debug(f'Updated {customer["customerID"]}')