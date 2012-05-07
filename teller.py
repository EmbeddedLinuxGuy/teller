import imapclient
from imapclient import IMAPClient
import sys, os
from ConfigParser import SafeConfigParser, NoOptionError

HOST = 'imap.mail.yahoo.com'
USERNAME = 'someuser'
PASSWORD = 'secret'
ssl = False

def parse_config_file(path):
    """Parse INI files containing IMAP connection details.

    Used by livetest.py and interact.py
    """
    parser = SafeConfigParser(dict(ssl='false',
                                   username=None,
                                   password=None,
                                   oauth='false',
                                   oauth_url=None,
                                   oauth_token=None,
                                   oauth_token_secret=None))
    fh = file(path)
    parser.readfp(fh)
    fh.close()
    section = 'main'
    assert parser.sections() == [section], 'Only expected a [main] section'

    try:
        port = parser.getint(section, 'port')
    except NoOptionError:
        port = None
        
    return Bunch(
        host=parser.get(section, 'host'),
        port=port,
        ssl=parser.getboolean(section, 'ssl'),
        username=parser.get(section, 'username'),
        password=parser.get(section, 'password'),
        oauth=parser.getboolean(section, 'oauth'),
        oauth_url=parser.get(section, 'oauth_url'),
        oauth_token=parser.get(section, 'oauth_token'),
        oauth_token_secret=parser.get(section, 'oauth_token_secret'),
    )

def create_client_from_config(conf):
    client = imapclient.IMAPClient(conf.host, port=conf.port, ssl=conf.ssl)
    if conf.oauth:
        client.oauth_login(conf.oauth_url,
                           conf.oauth_token,
                           conf.oauth_token_secret)
    else:
        client.login(conf.username, conf.password)
    return client

class Bunch(dict):

    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            raise AttributeError

    def __setattr__(self, k, v):
        self[k] = v

def parse_argv():
    args = sys.argv[1:]
    if not args:
        print ('Please specify a host configuration file. See livetest-sample.ini for an example.')
        sys.exit(1)
    ini_path = sys.argv.pop(1)  # 2nd arg should be the INI file
    if not os.path.isfile(ini_path):
        print ('%r is not a livetest INI file' % ini_path)
        sys.exit(1)
    host_config = parse_config_file(ini_path)
    return host_config

def probe_host(config):
    client = create_client_from_config(config)
    ns = client.namespace()
    client.logout()
    if not ns.personal:
        raise RuntimeError('Can\'t run tests: IMAP account has no personal namespace')
    return ns.personal[0]   # Use first personal namespace

host_config = parse_argv()
namespace = probe_host(host_config)
host_config.namespace = namespace

#print host_config
#{'username': '', 'oauth_token_secret': None, 'namespace': ('', None), 'ssl': True, 'host': 'imap.mail.yahoo.com', 'oauth_token': None, 'oauth': False, 'oauth_url': None, 'password': '', 'port': 993}

server = IMAPClient(host_config['host'], use_uid=True, ssl=host_config['ssl'])
server.login(host_config['username'], host_config['password'])

select_info = server.select_folder('INBOX')
print '%d messages in INBOX' % select_info['EXISTS']

messages = server.search(['NOT DELETED'])
print "%d messages that aren't deleted" % len(messages)

print
print "Messages:"
response = server.fetch(messages, ['FLAGS', 'RFC822.SIZE'])
for msgid, data in response.iteritems():
    print '   ID %d: %d bytes, flags=%s' % (msgid,
                                            data['RFC822.SIZE'],
                                            data['FLAGS'])
