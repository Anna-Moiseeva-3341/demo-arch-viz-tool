import re
from urllib.parse import urlparse

ADDRESS_KEY_PARTS = ("HOST", "URL", "URI", "DSN", "ADDR", "ENDPOINT")
HOSTNAME = re.compile(r"[A-Za-z0-9]([A-Za-z0-9_.-]*[A-Za-z0-9])?")

def is_address_key(key):
    return any(part in key.upper() for part in ADDRESS_KEY_PARTS)

def host_of(value):
    value = value.strip()
    if "://" in value:
        try:
            return urlparse(value).hostname
        except ValueError:
            return None
    host = value.split(":", 1)[0]
    return host.lower() if HOSTNAME.fullmatch(host) else None

def component_for(host, names):
    lowered = {name.lower(): component for name, component in names.items()}
    return lowered.get(host.lower())