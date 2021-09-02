import logging
import sys
import time
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


def delta_in_hours(last_visit, updated):
    return int((last_visit - updated) / timedelta(hours=1))


class TumblrHandler:

    def __init__(self, config, db_session):
        self._db_session = db_session

        self._calls_per_minute = int(config['tumblr-rate-limits']['calls_per_minute'])
        self._calls_per_hour = int(config['tumblr-rate-limits']['calls_per_hour'])
        self._calls_per_day = int(config['tumblr-rate-limits']['calls_per_day'])

        self._client = pytumblr.TumblrRestClient(
            config['tumblr-auth']['consumer_key'],
            config['tumblr-auth']['consumer_secret'],
            config['tumblr-auth']['oauth_token'],
            config['tumblr-auth']['oauth_secret'],
        )

    def _mark_call(self, timestamp, call, limit, duration):

        call = Call(time=timestamp, call=call, limit=limit, duration=duration)
        self._db_session.add(call)
        self._db_session.commit()

    def _wait_for_limits(self):
        tumblr_limits = self.get_limits()
        while tumblr_limits['exceeding_limit']:
            now = datetime.utcnow()
            delta = 70 - now.second
            logging.info('Sleep for [%i] seconds (limits [%s]).', delta, tumblr_limits)
            time.sleep(delta)
            tumblr_limits = self.get_limits()

    def get_limits(self):

        now = datetime.utcnow()

        day_overflow = timedelta(
            hours=now.hour,
            minutes=now.minute,
            seconds=now.second,
            microseconds=now.microsecond
        )
        hour_overflow = timedelta(
            minutes=now.minute,
            seconds=now.second,
            microseconds=now.microsecond
        )
        minute_overflow = timedelta(
            seconds=now.second,
            microseconds=now.microsecond
        )

        day = (now - day_overflow).strftime("%Y-%m-%d %H:%M:%S")
        hour = (now - hour_overflow).strftime("%Y-%m-%d %H:%M:%S")
        mins = (now - minute_overflow).strftime("%Y-%m-%d %H:%M:%S")

        day_used = self._db_session.query(func.count(Call.id)).filter(Call.time >= day).scalar()
        hour_used = self._db_session.query(func.count(Call.id)).filter(Call.time >= hour).scalar()
        minute_used = self._db_session.query(func.count(Call.id)).filter(Call.time >= mins).scalar()

        limits = {
            'day': self._calls_per_day - day_used,
            'hour': self._calls_per_hour - hour_used,
            'minute': self._calls_per_minute - minute_used,
        }

        if limits['minute'] < 5 or limits['hour'] < 5 or limits['day'] < 5:
            limits['exceeding_limit'] = True
        else:
            limits['exceeding_limit'] = False

        return limits

    def blog_info(self, blog_name):

        self._wait_for_limits()

        timestamp = datetime.utcnow()
        blog_data = self._client.blog_info(blog_name)
        delta = (datetime.utcnow() - timestamp) / timedelta(microseconds=1)
        self._mark_call(timestamp, CallFunc.BLOG_INFO, 1, delta)

        return blog_data

    def posts(self, blog_name, limit, offset):

        self._wait_for_limits()

        timestamp = datetime.utcnow()
        posts_data = self._client.posts(blog_name, limit=limit, offset=offset, notes_info=True)
        delta = (datetime.utcnow() - timestamp) / timedelta(microseconds=1)
        self._mark_call(timestamp, CallFunc.POSTS, limit, delta)

        return posts_data


class TumblrClient:

    def __init__(self, config, db_session):
        self._db_session = db_session
        self._tumblr = TumblrHandler(config, db_session)

        tumblr_limits = self._tumblr.get_limits()
        if tumblr_limits['exceeding_limit']:
            logging.error('Close to exceeding the limits: %s.', tumblr_limits)
            sys.exit(0)

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
            post_count=blog['posts'],
            updated=blog['updated'],
            last_visit=blog['last_visit'],
            last_post=blog['last_post'],
            age=blog['age'],
        )

        self._db_session.add(blog_record)
        self._db_session.commit()

        logging.info('Blog [%s] (%s) successfully saved.', blog['name'], blog['state'])

    def _save_not_found_blog(self, blog_name):
        blogs = self._db_session.query(Blog).filter(Blog.name == blog_name)
        blog_record = blogs.first()
        if blog_record:
            blog_record = {
                'state': BlogState.NOT_FOUND,
                'description': None,
                'url': None,
                'avatar': None,
                'posts': 0,
                'updated': datetime.utcnow(),
                'last_visit': datetime.utcnow(),
                'last_post': 0,
                'age': 0,
            }
            self._db_session.commit()
        else:
            blog = {
                'name': blog_name,
                'title': None,
                'state': BlogState.NOT_FOUND,
                'description': None,
                'url': None,
                'avatar': None,
                'posts': 0,
                'updated': datetime.utcnow(),
                'last_visit': datetime.utcnow(),
                'last_post': 0,
                'age': 0,
            }
            self._save_blog(blog)

    def _save_blog_info(self, state, blog_name):
        blog_data = self._tumblr.blog_info(blog_name)

        if 'errors' in blog_data:
            if blog_data['meta']['status'] == 404:
                self._save_not_found_blog(blog_name)
            else:
                logging.warning(
                    'Error [%i] occured while retrieving blog [%s].',
                    blog_data['meta']['status'],
                    blog_name
                )
        elif 'blog' in blog_data:
            blog = blog_data['blog']
            blog['avatar'] = get_avatar(blog)
            blog['state'] = state
            blog['updated'] = datetime.fromtimestamp(blog['updated'])
            blog['last_visit'] = datetime.utcnow()
            blog['age'] = delta_in_hours(blog['last_visit'], blog['updated'])
            blog['last_post'] = 0
            self._save_blog(blog)
        else:
            logging.warning('Error occured while retrieving blog data [%s].', blog_data)

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
            self._save_blog_info(BlogState.ENABLED, blog_name)

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
            self._save_blog_info(BlogState.POTENTIAL, blog_name)

    def update_blogs(self):

        stored_blogs = self._db_session.query(Blog).filter(Blog.state == BlogState.ENABLED)
        stored_blog_records = stored_blogs.all()
        for db_blog in stored_blog_records:
            recent_blog = self._tumblr.blog_info(db_blog.name)
            if 'errors' in recent_blog:
                if recent_blog['meta']['status'] == 404:
                    self._save_not_found_blog(db_blog.name)
                else:
                    logging.warning(
                        'Error [%i] occured while retrieving blog [%s].',
                        recent_blog['meta']['status'], db_blog.name)
            elif 'blog' in recent_blog:
                setattr(db_blog, 'post_count', recent_blog['blog']['posts'])
                setattr(db_blog, 'updated', datetime.fromtimestamp(recent_blog['blog']['updated']))
                setattr(db_blog, 'last_visit', datetime.utcnow())
                setattr(db_blog, 'age', delta_in_hours(db_blog.last_visit, db_blog.updated))
                #db_blog['last_post'] = 0
                self._db_session.commit()
            else:
                logging.warning('Error occured while retrieving blog data [%s].', recent_blog)

    def update_posts(self):
        count = 0

        stored_blogs = self._db_session.query(Blog).filter(Blog.state == BlogState.ENABLED)
        stored_blog_records = stored_blogs.all()
        for blog in stored_blog_records:
            count = count + blog.post_count - blog.last_post
        print(count)

#            posts_data = self._tumblr.posts(blog.name, limit=1, offset=0)
#            if 'posts' in posts_data:
#
#                print(json.dumps(posts_data, indent=2, sort_keys=True))
#                break
#
#                for post in posts_data['posts']:
#
#                    print(json.dumps(post, indent=2, sort_keys=True))
#                    break
#
#                    if 'notes' in post:
#                        for note in post['notes']:
#                            self.save_potential_blog(note['blog_name'])
#                break
#            break
#
    def limits(self):
        print(self._tumblr.get_limits())
