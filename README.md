# pyLightspeed
Trying to make working with the Lightspeed API more polite. (pyLight? anyone? no? I thought it was good.)

Right now this is in progress and focused on the POS side. eCom side will come soon. This is super under construction. I am not maintaining good git habits yet, this is just me working. Use at your own risk.

## Usage

1. Create lightspeed_keys json files with your keys. I know this isn't best practice - you should store them in environment variables - but for my purposes and to make it easier for people who aren't as familier, I am holding them in a json file. See the example\data directory for an example
2. You will need to request your authorization token manually and paste it in the code, then run the code (before the 30 second time out). Refer to Lightspeed's doc on [Requesting a temporary token](https://developers.lightspeedhq.com/retail/authentication/authentication-overview/#requesting-an-access-token) for their overview, and refer to comments in api.py and replace `CODE = "XXXXX"` with your temporary token.
3. Look at examples\ex_simple_connection.py or export_to_csv.ipynb. The rest of the stuff in examples is mostly me playing around trying to figure things out.

## Update June 2021

Realized I had not updated this in over a year, so sync'd it up. This is still a mess of my random stuff - basically a dump of stuff from my HD, but a lot of it works. I am actually using the api_dev.py as my main version. Made some changes to help me use the same code to connect to multiple instances of lightspeed. 
