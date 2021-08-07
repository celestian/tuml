import logging
from datetime import datetime
import json
import pytumblr

from db.tables import Blog, BlogState

def get_avatar(blog):
    avatar_url = None

    for avatar in blog['avatar']:
        if avatar['height'] == 64:
            avatar_url = avatar['url']

    return avatar_url


class TumblrClient:

    def __init__(self, config, db_session):
        self._client = pytumblr.TumblrRestClient(
            config['tumblr-auth']['consumer_key'],
            config['tumblr-auth']['consumer_secret'],
            config['tumblr-auth']['oauth_token'],
            config['tumblr-auth']['oauth_secret'],
        )
        self._db_session = db_session

    def enable_blog(self, blog_name):
        blog_data = self._client.blog_info(blog_name)

        if 'errors' in blog_data:
            if blog_data['meta']['status'] == 404:
                logging.error('Blog [%s] not found.', blog_name)
            else:
                logging.critical(
                    'Error [%i] occured while retrieving blog [%s].',
                    blog_data['meta']['status'],
                    blog_name
                )

        if 'blog' in blog_data:
            blog = blog_data['blog']

            existing_blog = self._db_session.query(Blog).filter(Blog.name == blog['name'])
            existing_blog_record = existing_blog.first()
            if existing_blog_record:
                if existing_blog_record.state == BlogState.ENABLED:
                    logging.warning('Blog [%s] is already enabled.', blog['name'])
                else:
                    logging.info('Blog [%s] is [%s]', blog['name'], existing_blog_record.state)
                    existing_blog_record.state = BlogState.ENABLED
                    self._db_session.add(existing_blog_record)
                    self._db_session.commit()

                    logging.info('Blog [%s] successfully enabled again.', blog['name'])

            else:

                blog_record = Blog(
                    name=blog['name'],
                    title=blog['title'],
                    state=BlogState.ENABLED,
                    description=blog['description'],
                    url=blog['url'],
                    avatar=get_avatar(blog),
                    posts=blog['posts'],
                    updated=datetime.fromtimestamp(blog['updated'])
                )

                self._db_session.add(blog_record)
                self._db_session.commit()

                logging.info('Blog [%s] successfully enabled.', blog['name'])
