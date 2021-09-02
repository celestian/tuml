import logging
import pathlib
import jinja2

from db.tables import Blog, BlogState


class OutputHandler:

    def __init__(self, config, db_session):
        self._db_session = db_session

        template_loader = jinja2.FileSystemLoader(searchpath='./tuml/templates')
        self._template_env = jinja2.Environment(loader=template_loader)

        self._index_file = './index.html'

    def generate(self):

        stored_blogs = self._db_session.query(Blog).filter(
            Blog.state == BlogState.POTENTIAL).order_by(
            Blog.posts.desc())
        blogs = stored_blogs.all()

        self._template_env.get_template('index.html').stream(blogs=blogs).dump(self._index_file)
