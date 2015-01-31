import sys
import json
from itertools import chain, count
from getpass import getpass

from mechanize import Browser

import urls
import constants

class ForumAutomation:
    def __init__(self, username, password):
        self.username = username
        self.password = password

        self.br = Browser()

    def login(self):
        self.br.open(urls.LOGIN_URL)
        self.br.select_form(nr=1)

        self.br[constants.USERNAME] = self.username
        self.br[constants.PASSWORD] = self.password

        self.br.submit()

    def get_banned(self):
        "return tuple (banned, duplicates) where both are sets"
        self.br.open(urls.IP_BAN_URL)

        items = list(self.br.forms())[1].controls[-3].get_items()
        ip_addrs = [item.attrs[constants.CONTENTS] for item in items]

        banned = set()
        dupes = set()
        for addr in chain(*map(expand, ip_addrs)):
            if addr in banned:
                dupes.add(addr)
            else:
                banned.add(addr)

        return (banned, dupes)

    def get_newly_registered_members_ids(self, start=0):
        "generator, which will do i/o between calls"
        for offset in count(start, 25):
            # should build one with MEMBERS_LIST_URL
            resp = self.br.open(urls.NEW_REGISTERED_MEMBERS_URL.format(offset))
            if constants.NO_MEMBERS_FOUND in resp.read():
                break

            for link in self.br.links():
                if link.url.startswith(constants.VIEW_PROFILE):
                    yield int(link.url.split('=')[-1])

    def get_profile(self, member_id):
        "current returns (website, None, None); need to add interests, signature, create class to house this information"
        self.br.open(urls.PROFILE_URL.format(member_id))

        for link in self.br.links():
            attrs = dict(link.attrs)
            if attrs.get(constants.TITLE, "").startswith(constants.VISIT_WEBSITE):
                website = attrs[constants.HREF]

        return (website, None, None)

        #TODO: get interests and signature

    def go_to_admin_control_panel(self):
        self.br.open(urls.INDEX_PAGE)

        # the last URL on the page should be to the admin page
        self.br.follow_link(list(self.br.links())[-1])

    def admin_login(self):
        self.go_to_admin_control_panel()

        # the second form is the login form; the first is a search box
        self.br.select_form(nr=1)

        # the password form param is variable
        self.br[self.br.form.controls[1].id] = self.password
        self.br[constants.USERNAME] = self.username

        self.br.submit()

    def backup(self, filename=None):
        "login and admin_login are expected to be called first"

        self.go_to_admin_control_panel()

        # go to the maintenance tab
        for link in self.br.links():
            if constants.MAINTENANCE in link.text:
                self.br.follow_link(link)
                break

        # go to the backup section (left bar)
        for link in self.br.links():
            if constants.BACKUP in link.url:
                self.br.follow_link(link)
                break

        backup_form = next(self.br.forms())

        # download everything using bzip2
        self.br.select_form(nr=0)
        self.br[constants.METHOD] = [constants.BZIP2]
        self.br[constants.WHERE] = [constants.DOWNLOAD]
        self.br[constants.TABLE] = constants.ALL_TABLES

        print "  Submitting form..."
        resp = self.br.submit()
        if filename is None:
            filename = resp.info().plist[0].split('="')[-1].strip("'\"")
        print "  Downloading file..."
        with open(filename, "wb") as backup:
            backup.write(resp.get_data())
        print "  Saved", filename

def print_banned_stats(banned, dupes):
    print "Total banned IPs:", len(banned)
    print "Percent of IPv4 addresses: {:.3f}%".format(len(banned) * 100.0 / 2**32)
    print "Total duplicate entries:", len(dupes)

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
    if len(sys.argv) == 2:
        with open(sys.argv[1]) as login_file:
            credentials = json.load(login_file)
            username = credentials[constants.USERNAME]
            password = credentials[constants.PASSWORD]
    else:
        username = raw_input("Username: ")
        password = getpass()

    forum = ForumAutomation(username, password)

    print "Logging in..."
    forum.login()

    print "Logging into the admin control panel..."
    forum.admin_login()

    if raw_input("Backup? ").lower().startswith('y'):
        print "Backing up forum..."
        forum.backup()
