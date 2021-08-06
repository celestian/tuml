"""tuml

Usage:
  tuml [--cfg=<config_file>] <gallery>
  tuml (-h | --help)
  tuml --version

Options:
  --cfg=<config_file>   Configuration file [default: ./tuml.cfg].
  -h --help             Show this screen.
  --version             Show version.
"""

import logging
import configparser
from docopt import docopt
import json
import pytumblr


def configuration_setup(args):

    cfg = {}

    cfg_parser = configparser.ConfigParser()
    cfg_parser.read(args['--cfg'])

    for section in cfg_parser.sections():
        cfg[section] = {}
        for key in cfg_parser.options(section):
            cfg[section][key] = cfg_parser.get(section, key)

    if cfg['tuml']['log_level'] == 'debug':
        logging.basicConfig(level=logging.DEBUG)
    elif cfg['tuml']['log_level'] == 'info':
        logging.basicConfig(level=logging.INFO)
    elif cfg['tuml']['log_level'] == 'warning':
        logging.basicConfig(level=logging.WARNING)
    elif cfg['tuml']['log_level'] == 'error':
        logging.basicConfig(level=logging.ERROR)
    elif cfg['tuml']['log_level'] == 'critical':
        logging.basicConfig(level=logging.CRITICAL)
    else:
        logging.basicConfig(level=logging.INFO)
        logging.warning('Missing members-db/log_level in configuration file [%s]', args['--cfg'])

    return cfg


def main():

    args = docopt(__doc__, version='0.0.1')
    config = configuration_setup(args)

    client = pytumblr.TumblrRestClient(
        config['tumblr-auth']['consumer_key'],
        config['tumblr-auth']['consumer_secret'],
        config['tumblr-auth']['oauth_token'],
        config['tumblr-auth']['oauth_secret'],
    )

    print('===== blog_info ------------------------------------------')
    hmm = client.blog_info(args['<gallery>'])
    print(json.dumps(hmm, indent=2, sort_keys=True))

    blog = hmm['blog']

#    print('===== posts ------------------------------------------')
#    hmmm = client.posts(args['<gallery>'], limit=1, offset=0, reblog_info=True, notes_info=True)
#    print(json.dumps(hmmm, indent=2, sort_keys=True))

#    print(f"{blog['name']} {blog['title']} {blog['posts']} {blog['updated']} {blog['url']} {blog['description']}")
#    logging.info('User [%s] succesfully added.', admin_email)


if __name__ == '__main__':
    main()
