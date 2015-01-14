import json
from itertools import chain

from mechanize import Browser

LOGIN_FILE = "login.json"

LOGIN_URL = "http://python-forum.org/ucp.php?mode=login"
IP_BAN_URL = "http://python-forum.org/mcp.php?i=ban&mode=ip"

def login(br):
    br.open(LOGIN_URL)
    br.select_form(nr=1)

    with open(LOGIN_FILE) as login_file:
        credentials = json.load(login_file)
        br["username"] = credentials["username"]
        br["password"] = credentials["password"]

    br.submit()

def get_banned(br):
    'return tuple (banned, duplicates) where both are sets'
    br.open(IP_BAN_URL)

    items = list(br.forms())[1].controls[-3].get_items()
    ip_addrs = [item.attrs["contents"] for item in items]

    banned = set()
    dupes = set()
    for addr in chain(*map(expand, ip_addrs)):
        if addr in banned:
            dupes.add(addr)
        else:
            banned.add(addr)

    return (banned, dupes)

def print_banned_stats(banned, dupes):
    print 'Total banned IPs:', len(banned)
    print 'Percent of IPv4 addresses: {:.3f}%'.format(len(banned) * 100.0 / 2**32)
    print 'Total duplicate entries:', len(dupes)

def expand(pat):
    "expand an IP address string with wild cards, e.g. 10.0.0.* -> [10.0.0.0, 10.0.0.1, ..., 10.0.0.255]"
    if '*' not in pat:
        yield pat
    else:
        template = pat.replace("*", "{}", 1)
        for x in xrange(256):
            for expanded in expand(template.format(x)):
                yield expanded

if __name__ == "__main__":
    br = Browser()
    login(br)
