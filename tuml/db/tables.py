import enum
from sqlalchemy import Column, Integer, Text, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base


DB_Base = declarative_base()


class BlogState(enum.Enum):
    ENABLED = 1
    DISABLED = 2
    POTENTIAL = 3
    NOT_FOUND = 4


class Blog(DB_Base):
    __tablename__ = "blogs"
    __mapper_args__ = {"eager_defaults": True}

    name = Column(Text, primary_key=True)
    title = Column(Text)
    state = Column(Enum(BlogState))
    description = Column(Text)
    url = Column(Text)
    avatar = Column(Text)
    posts = Column(Integer)
    updated = Column(DateTime)
