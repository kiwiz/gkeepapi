#!/usr/bin/env python3
import sys
import keyring
import getpass
import logging
import gkeepapi

USERNAME = "user@gmail.com"


# Set up logging
logger = logging.getLogger("gkeepapi")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("[%(levelname)s] %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

# Initialize the client
keep = gkeepapi.Keep()

token = keyring.get_password("google-keep-token", USERNAME)
store_token = False

if not token:
    token = getpass.getpass("Master token: ")
    store_token = True

# Authenticate using a master token
logger.info("Authenticating")
try:
    keep.authenticate(USERNAME, token, sync=False)
    logger.info("Success")
except gkeepapi.exception.LoginException:
    logger.error("Failed to authenticate")
    sys.exit(1)

if store_token:
    keyring.set_password("google-keep-token", USERNAME, token)

# Sync state down
keep.sync()

# Application logic
# ...
