#!/usr/bin/env python3
import sys
import os
import argparse
import yaml
import keyring
import getpass
import logging
import time
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
logged_in = False

# Use an existing master token if one exists
if token:
    logger.info("Authenticating with token")
    try:
        keep.resume(USERNAME, token, sync=False)
        logged_in = True
        logger.info("Success")
    except gkeepapi.exception.LoginException:
        logger.info("Invalid token")

# Otherwise, prompt for credentials and login
if not logged_in:
    password = getpass.getpass()
    try:
        keep.login(USERNAME, password, sync=False)
        logged_in = True
        del password
        token = keep.getMasterToken()
        keyring.set_password("google-keep-token", USERNAME, token)
        logger.info("Success")
    except gkeepapi.exception.LoginException as e:
        logger.info(e)

# Abort if authentication failed
if not logged_in:
    logger.error("Failed to authenticate")
    sys.exit(1)

# Sync state down
keep.sync()

# Application logic
# ...
