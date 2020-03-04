# pyLightspeed
Trying to make working with the Lightspeed API more polite. (pyLight? anyone? no? I thought it was good.)

Right now this is in progress and focused on the POS side. eCom side will come soon.

##What Works
You can use this to make calls to the api with some code tweaks at this point.
1. You will need to manuall get the Access token, and then paste it in and run this code (in less than 30 second, the token expires). I will be adding some code to call a flask instance to do this within the code, but since this only really needs to be done once, it hasn't been top priority. The code
2. Once you have the access token pasted in, you will use the refresh tokens. See code comments.

This is super under construction. I am not maintaining good git habits yet, this is just me working. Use at your own risk.
