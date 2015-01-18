import json
from itertools import chain, count

from mechanize import Browser

LOGIN_FILE = "login.json"

LOGIN_URL = "http://python-forum.org/ucp.php?mode=login"
IP_BAN_URL = "http://python-forum.org/mcp.php?i=ban&mode=ip"
NEW_REGSITERED_MEMBERS_URL = "http://python-forum.org/memberlist.php?start={}&g=7"
PROFILE_URL = "http://python-forum.org/memberlist.php?mode=viewprofile&u={}"

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

def get_members_ids(br, start=0):
    'generator, which will do i/o between calls'
    for offset in count(start, 25):
        resp = br.open(NEW_REGSITERED_MEMBERS_URL.format(offset))
        if 'No members found for this search criterion.' in resp.read():
            break

        for link in br.links():
            if link.url.startswith('./memberlist.php?mode=viewprofile&u='):
                yield link.url.split('=')[-1]

def get_profile(br, member_id):
    br.open(PROFILE_URL.format(member_id))

    for link in br.links():
        attrs = dict(link.attrs)
        if attrs.get("title", "").startswith("Visit website:"):
            website = attrs["href"]

    #TODO: get interests and signature

def backup_forum(br):
    br.follow_link(list(br.links())[-1])
    br.select_form(nr=1)

    with open(LOGIN_FILE) as login_file:
        credentials = json.load(login_file)
        br["username"] = credentials["username"]
        br[br.form.controls[1].id] = credentials["password"]

    br.submit()

    for link in br.links():
        if 'Maintenance' in link.text:
            br.follow_link(link)
            break

    for link in br.links():
        if 'backup' in link.url:
            br.follow_link(link)
            break

    backup_form = next(br.forms())

    br.select_form(nr=0)
    br["method"] = ["bzip2"]
    br["where"] = ["download"]
    br["table[]"] = ['phpbb_acl_groups', 'phpbb_acl_options', 'phpbb_acl_roles', 'phpbb_acl_roles_data', 'phpbb_acl_users', 'phpbb_attachments', 'phpbb_banlist', 'phpbb_bbcodes', 'phpbb_bookmarks', 'phpbb_bots', 'phpbb_config', 'phpbb_confirm', 'phpbb_disallow', 'phpbb_drafts', 'phpbb_extension_groups', 'phpbb_extensions', 'phpbb_forums', 'phpbb_forums_access', 'phpbb_forums_track', 'phpbb_forums_watch', 'phpbb_groups', 'phpbb_icons', 'phpbb_lang', 'phpbb_log', 'phpbb_login_attempts', 'phpbb_moderator_cache', 'phpbb_modules', 'phpbb_poll_options', 'phpbb_poll_votes', 'phpbb_posts', 'phpbb_privmsgs', 'phpbb_privmsgs_folder', 'phpbb_privmsgs_rules', 'phpbb_privmsgs_to', 'phpbb_profile_fields', 'phpbb_profile_fields_data', 'phpbb_profile_fields_lang', 'phpbb_profile_lang', 'phpbb_ranks', 'phpbb_reports', 'phpbb_reports_reasons', 'phpbb_search_results', 'phpbb_search_wordlist', 'phpbb_search_wordmatch', 'phpbb_sessions', 'phpbb_sessions_keys', 'phpbb_sitelist', 'phpbb_smilies', 'phpbb_styles', 'phpbb_styles_imageset', 'phpbb_styles_imageset_data','phpbb_styles_template', 'phpbb_styles_template_data', 'phpbb_styles_theme', 'phpbb_topics', 'phpbb_topics_posted', 'phpbb_topics_track', 'phpbb_topics_watch','phpbb_user_group', 'phpbb_users', 'phpbb_warnings', 'phpbb_words', 'phpbb_zebra']

    print "  Submitting form..."
    resp = br.submit()
    filename = resp.info().plist[0].split('="')[-1].strip("'\"")
    print "  Downloading file..."
    with open(filename, "wb") as backup:
        backup.write(resp.get_data())
    print "  Saved", filename

if __name__ == "__main__":
    br = Browser()
    print "Logging in..."
    login(br)
    print "Backing up forum..."
    backup_forum(br)
