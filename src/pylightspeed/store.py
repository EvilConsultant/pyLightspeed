#  LightspeedStore object to make it easier to connect to multiple stores, move data between stores, run scripts on multiple stores, etc.
#  In my use case, I deal iwth multiple clients and multiple stores, so implementing this as a way to make those tasks easier.
#  You can always skip this, as there are several things here that are not needed just for using the API, and you can just use the API directly.

import json
import time
import os


class LightspeedStore(object):
    """Holds connection parameters for one Lightspeed store.

    A convenience wrapper that makes it easier to use pyLightspeed with multiple
    stores or clients. You can skip this class entirely and pass credentials
    directly to the API constructors.

    Args:
        keyfile (str): Path to a JSON file containing the API connection parameters
            and credential values.
        codefile (str): Path for the JSON file that will hold the OAuth refresh
            token. Defaults to ``\"codes.json\"``.
    """

    def __init__(self, keyfile, codefile="codes.json"):
        with open(keyfile) as f:
            keyfile_data = json.load(f)
        # I know I could use something like json.loads(data, object_hook=lambda d: SimpleNamespace(**d)) to roll this into an object, but listing them out so it is obvious
        # just going to save a bunch of stuff in case we need it later
        self.keyfile = keyfile  # might need it later?
        # Settings for Lightspeed Retail API and Oauth
        self.retail_api_host = keyfile_data[
            "retail_api_host"
        ]  # E.g. "retail_api_host": "api.lightspeedapp.com"
        self.retail_api_path = keyfile_data[
            "retail_api_path"
        ]  # E.g. "retail_api_path": "API/Account/{}/{}/"  The {} allows the connection object to inject the account_id
        self.account_id = keyfile_data["account_id"]
        self.client_id = keyfile_data["client_id"]
        self.client_secret = keyfile_data["client_secret"]
        # Settings for Lightspeed eCom API
        self.api_key = keyfile_data["api_key"]
        self.api_secret = keyfile_data["api_secret"]
        self.ecom_api_host = keyfile_data["ecom_api_host"]

        # Paths for various files/uses
        self.codes_path = keyfile_data[
            "codes_path"
        ]  # E.g. "codes_path": "D:\\Development\\.keys\\"  I don't think this is needed as I am just using the full path for codes_file
        # Changing this so it works with .codes folder in the root of the project
        self.token_file = f"{os.getcwd()}{keyfile_data['codes_file']}"  # E.g. "codes_file" : "D:\\Development\\.keys\\my_codes.json" Provide full path to the file you want to use
        self.export_path = keyfile_data[
            "export_path"
        ]  # E.g. "export_path": "D:\\Data\\ETLs\\API Exports\\"
        self.database = keyfile_data[
            "database"
        ]  # E.g. "database":"mysql+mysqlconnector://user:password@localhost:3306/my_database" Obvioulsly, for if you want to connect to a DB.
        self.database_engine = keyfile_data[
            "database_engine"
        ]  # E.g. "database_engine": "mysql+mysqlconnector"
        self.database_user = keyfile_data[
            "database_user"
        ]  # E.g. "database_user": "user"
        self.database_password = keyfile_data[
            "database_password"
        ]  # E.g. "database_password": "password"
        self.database_host = keyfile_data[
            "database_host"
        ]  # E.g. "database_host": "localhost"
        self.database_port = keyfile_data["database_port"]  # E.g. "database_port": 3306
        self.database_name = keyfile_data[
            "database_name"
        ]  # E.g. "database_name": "my_database"

        # Load the refresh token if it exists
        try:
            with open(self.token_file, "r") as f:
                codes = json.load(f)
            self.access_token = codes["access_token"]
            self.expires_in = codes["expires_in"]
            self.token_type = codes["token_type"]
            self.scope = codes["scope"]
            self.refresh_token = codes["refresh_token"]
            self.last_run = codes["last_run"]

        except FileNotFoundError as err:
            print("No codes file found. Creating one now.")
            codes = {}

            try:
                with open(self.token_file, "w") as f:
                    json.dump(codes, f)
            except FileNotFoundError as err:
                print(
                    f"Could not create codes file in {self.token_file}. Check the path and permissions."
                )
                raise err

        return

    def save_codes(self):
        new_codes = {
            "access_token": self.access_token,
            "expires_in": self.expires_in,
            "token_type": self.token_type,
            "scope": self.scope,
            "refresh_token": self.refresh_token,
            "last_run": time.time(),
        }
        with open(self.token_file, "w") as outfile:
            json.dump(new_codes, outfile, indent=4)
