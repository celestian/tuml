import logging
import sys
from datetime import datetime
from datetime import timedelta
import json
import pytumblr
from sqlalchemy import func

from db.tables import Blog, BlogState, Call, CallFunc


def get_avatar(blog):
    avatar_url = None

    for avatar in blog['avatar']:
        if avatar['height'] == 64:
            avatar_url = avatar['url']

    return avatar_url


class TumblrHandler:

    def __init__(self, config, db_session):
        self._db_session = db_session

        self._calls_per_minute = config['tumblr-rate-limits']['calls_per_minute']
        self._calls_per_hour = config['tumblr-rate-limits']['calls_per_hour']
        self._calls_per_day = config['tumblr-rate-limits']['calls_per_day']

        self._client = pytumblr.TumblrRestClient(
            config['tumblr-auth']['consumer_key'],
            config['tumblr-auth']['consumer_secret'],
            config['tumblr-auth']['oauth_token'],
            config['tumblr-auth']['oauth_secret'],
        )

    def _get_limits(self):

        now = datetime.utcnow()

        day_overflow = timedelta(
            hours=now.hours,
            minutes=now.minutes,
            seconds=now.seconds,
            milliseconds=now.milliseconds,
            microseconds=now.microseconds
        )
        hour_overflow = timedelta(
            minutes=now.minutes,
            seconds=now.seconds,
            milliseconds=now.milliseconds,
            microseconds=now.microseconds
        )
        minute_overflow = timedelta(
            seconds=now.seconds,
            milliseconds=now.milliseconds,
            microseconds=now.microseconds
        )

        day = (now - day_overflow).isoformat()
        hour = (now - hour_overflow).isoformat()
        mins = (now - minute_overflow).isoformat()

        day_used = self._db_session.query(func.count(Call.id)).filter(Call.dt >= day).scalar()
        hour_used = self._db_session.query(func.count(Call.id)).filter(Call.dt >= hour).scalar()
        minute_used = self._db_session.query(func.count(Call.id)).filter(Call.dt >= mins).scalar()

        return {
            'day': self._calls_per_day - day_used,
            'hour': self._calls_per_hour - hour_used,
            'minute': self._calls_per_minute - minute_used,
        }

    def blog_info(self, blog_name):

        limits = self._get_limits()
        if limits['minute'] < 5 or limits['hour'] < 5 or limits['day'] < 5:
            logging.error('Close to exceeding the limits: $s.', limits)
            sys.exit(0)

        dt_start = datetime.utcnow()
        blog_data = self._client.blog_info(blog_name)
        delta = datetime.utcnow() - dt_start
        print(delta / timedelta(microseconds=1))

        return blog_data

    def posts(self, blog_name, limit, offset):

        limits = self._get_limits()
        if limits['minute'] < 5 or limits['hour'] < 5 or limits['day'] < 5:
            logging.error('Close to exceeding the limits: $s.', limits)
            sys.exit(0)

        dt_start = datetime.utcnow()
        posts_data = self._client.posts(blog_name, limit, offset, notes_info=True)
        delta = datetime.utcnow() - dt_start
        print(delta / timedelta(microseconds=1))

        return posts_data


class TumblrClient:

    def __init__(self, config, db_session):
        self._db_session = db_session
        self._tumblr = TumblrHandler(config, db_session)

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
            blog_data = self._tumblr.blog_info(blog_name)

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

    def save_potential_blog(self, blog_name):

        stored_blogs = self._db_session.query(Blog).filter(Blog.name == blog_name)
        stored_blog_record = stored_blogs.first()
        if stored_blog_record:
            logging.info('Blog [%s] is marked as (%s).', blog_name, stored_blog_record.state)
        else:
            # self._resource.check()
            blog_data = self._tumblr.blog_info(blog_name)

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
                blog['state'] = BlogState.POTENTIAL
                blog['updated'] = datetime.fromtimestamp(blog['updated'])
                self._save_blog(blog)
            else:
                logging.warning('Error occured while retrieving blog data [%s].', blog_data)

    def update_blogs(self):

        stored_blogs = self._db_session.query(Blog).filter(Blog.state == BlogState.ENABLED)
        stored_blog_records = stored_blogs.all()
        for blog in stored_blog_records:
            posts_data = self._tumblr.posts(blog.name, limit=1, offset=0)
            if 'posts' in posts_data:
                for post in posts_data['posts']:
                    if 'notes' in post:
                        for note in post['notes']:
                            self.save_potential_blog(note['blog_name'])
            break
