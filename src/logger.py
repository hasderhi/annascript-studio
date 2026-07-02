import time

RED = "\033[0;31m"
GREEN = "\033[0;32m"
BLUE = "\033[0;34m"
PURPLE = "\033[0;35m"
YELLOW = "\033[1;33m"
END = "\033[0m"

TITLE = f"{"\033[0;37m"}[aScript]{"\033[0m"}"
DEBUG = f"{"\033[0;35m"}[DEBUG]{"\033[0m"}"
SUCCESS = f"{"\033[0;32m"}[SUCCESS]{"\033[0m"}"
INFO = f"{"\033[0;34m"}[INFO]{"\033[0m"}"
WARNING = f"{"\033[1;33m"}[WARNING]{"\033[0m"}"
ERROR = f"{"\033[0;31m"}[ERROR]{"\033[0m"}"

def get_timestamp():
    timestamp = time.ctime().split()
    return f"[{timestamp[3]}]"

def title(version):
    print(TITLE, PURPLE, f"annaScript Studio {version} - Copyright (c) 2025-2026 Annabeth Kisling", END)

def website():
    print(TITLE, PURPLE, "Support: https://tk-dev-software.com/annascript", END)

def debug(msg):
    print(TITLE, get_timestamp(), DEBUG, PURPLE, msg, END)

def success(msg):
    print(TITLE, get_timestamp(), SUCCESS, GREEN, msg, END)

def info(msg):
    print(TITLE, get_timestamp(), INFO, BLUE, msg, END)

def warning(msg):
    print(TITLE, get_timestamp(), WARNING, YELLOW, msg, END)

def error(msg):
    print(TITLE, get_timestamp(), ERROR, RED, msg, END)