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

    def _change_blog_state(self, blog, from_state, to_state):
        if blog.state == from_state:
            blog.state = to_state
            self._db_session.add(blog)
            self._db_session.commit()
            logging.info('Blog [%s] state changed: (%s --> %s).', blog.name, from_state, to_state)

    def _save_blog(self, blog):

        blog_record = Blog(
            name=blog['name'],
            title=blog['title'],
            state=blog['state'],
            description=blog['description'],
            url=blog['url'],
            avatar=blog['avatar'],
            posts=blog['posts'],
            updated=blog['updated']
        )

        self._db_session.add(blog_record)
        self._db_session.commit()

        logging.info('Blog [%s] (%s) successfully saved.', blog['name'], blog['state'])

    def enable_blog(self, blog_name):

        stored_blogs = self._db_session.query(Blog).filter(Blog.name == blog_name)
        stored_blog_record = stored_blogs.first()
        if stored_blog_record:
            if stored_blog_record.state == BlogState.ENABLED:
                logging.info('Blog [%s] is already enabled.', blog_name)
            elif stored_blog_record.state == BlogState.NOT_FOUND:
                logging.info('Blog [%s] is marked as (%s).', blog_name, BlogState.NOT_FOUND)
            else:
                self._change_blog_state(stored_blog_record, BlogState.DISABLED, BlogState.ENABLED)
                self._change_blog_state(stored_blog_record, BlogState.POTENTIAL, BlogState.ENABLED)
        else:
            blog_data = self._client.blog_info(blog_name)
            # TODO: markni, ze jsme pouzili resource

            if 'errors' in blog_data:
                if blog_data['meta']['status'] == 404:
                    blog = {
                        'name': blog_name,
                        'title': None,
                        'state': BlogState.NOT_FOUND,
                        'description': None,
                        'url': None,
                        'avatar': None,
                        'posts': 0,
                        'updated': datetime.utcnow(),
                    }
                    self._save_blog(blog)
                else:
                    logging.warning(
                        'Error [%i] occured while retrieving blog [%s].',
                        blog_data['meta']['status'],
                        blog_name
                    )
            elif 'blog' in blog_data:
                blog = blog_data['blog']
                blog['avatar'] = get_avatar(blog)
                blog['state'] = BlogState.ENABLED
                blog['updated'] = datetime.fromtimestamp(blog['updated'])
                self._save_blog(blog)
            else:
                logging.warning('Error occured while retrieving blog data [%s].', blog_data)

    def disable_blog(self, blog_name):

        stored_blogs = self._db_session.query(Blog).filter(Blog.name == blog_name)
        stored_blog_record = stored_blogs.first()
        if stored_blog_record:
            if stored_blog_record.state == BlogState.DISABLED:
                logging.info('Blog [%s] is already disabled.', blog_name)
            elif stored_blog_record.state == BlogState.NOT_FOUND:
                logging.info('Blog [%s] is marked as (%s).', blog_name, BlogState.NOT_FOUND)
            else:
                self._change_blog_state(stored_blog_record, BlogState.ENABLED, BlogState.DISABLED)
                self._change_blog_state(stored_blog_record, BlogState.POTENTIAL, BlogState.DISABLED)
