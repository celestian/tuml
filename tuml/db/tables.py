import enum
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Text
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy.ext.declarative import declarative_base


DB_Base = declarative_base()


class BlogState(enum.Enum):
    enabled = 1
    disabled = 2
    not_found = 3


class Blog(DB_Base):
    __tablename__ = "blogs"
    __mapper_args__ = {"eager_defaults": True}

    title = Column(Text, primary_key=True)
    state = Column(Enum(BlogState))
    description = Column(Text)
    url = Column(Text)
    avatar = Column(Text)
    posts = Column(Integer)
    updated = Column(Datetime)
