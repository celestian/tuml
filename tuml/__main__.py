"""tuml

Usage:
  tuml [--cfg=<config_file>] init
  tuml [--cfg=<config_file>] enable <blog>...
  tuml (-h | --help)
  tuml --version

Options:
  --cfg=<config_file>   Configuration file [default: ./tuml.cfg].
  -h --help             Show this screen.
  --version             Show version.
"""

import os
import logging
import json
import configparser
from docopt import docopt

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.tables import DB_Base
from tumblr_client import TumblrClient


def configuration_setup(args):

    cfg = {}

    cfg_parser = configparser.ConfigParser()
    cfg_parser.read(args['--cfg'])

    for section in cfg_parser.sections():
        cfg[section] = {}
        for key in cfg_parser.options(section):
            cfg[section][key] = cfg_parser.get(section, key)

    if cfg['tuml']['log_level'] == 'debug':
        logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
    elif cfg['tuml']['log_level'] == 'info':
        logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)
    elif cfg['tuml']['log_level'] == 'warning':
        logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.WARNING)
    elif cfg['tuml']['log_level'] == 'error':
        logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.ERROR)
    elif cfg['tuml']['log_level'] == 'critical':
        logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.CRITICAL)
    else:
        logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)
        logging.warning('Missing members-db/log_level in configuration file [%s]', args['--cfg'])

    cfg['db']['file'] = os.path.abspath(os.path.expanduser(cfg['db']['file']))

    return cfg


def main():

    args = docopt(__doc__, version='0.0.1')
    config = configuration_setup(args)

    if args['init']:

        if os.path.exists(config['db']['file']):
            os.remove(config['db']['file'])
            logging.info('Old database [%s] removed', config['db']['file'])

        db_engine = create_engine(f"sqlite:///{config['db']['file']}", echo=False)
        DB_Base.metadata.drop_all(db_engine)
        DB_Base.metadata.create_all(db_engine)
        logging.info('New database [%s] initiated.', config['db']['file'])

        return 0

    if args['enable']:

        db_engine = create_engine(f"sqlite:///{config['db']['file']}", echo=False)
        sql_session = sessionmaker(bind=db_engine)
        db_session = sql_session()

        client = TumblrClient(config, db_session)

        for blog in args['<blog>']:
            client.enable_blog(blog)

        return 0

#    hmmm = client.posts(args['<gallery>'], limit=1, offset=0, reblog_info=True, notes_info=True)


if __name__ == '__main__':
    main()
