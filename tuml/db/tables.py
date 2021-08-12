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


class Post(DB_Base):
    __tablename__ = "posts"
    __mapper_args__ = {"eager_defaults": True}

    sid = Column(Text, primary_key=True)
    blog_name = Column(Text)
    post_type = Column(Text)
    created = Column(DateTime)
    img_500 = Column(Text)
    img_400 = Column(Text)
    img_250 = Column(Text)
    img_100 = Column(Text)
    img_75 = Column(Text)
    img = Column(Text)


class CallFunc(enum.Enum):
    INFO = 1
    AVATAR = 2
    LIKES = 3
    FOLLOWING = 4
    DASHBOARD = 5
    TAGGED = 6
    POSTS = 7
    BLOG_INFO = 8
    BLOG_FOLLOWING = 9
    FOLLOWERS = 10
    BLOG_LIKES = 11
    QUEUE = 12
    DRAFTS = 13
    SUBMISSION = 14
    FOLLOW = 15
    UNFOLLOW = 16
    LIKE = 17
    UNLIKE = 18
    CREATE_PHOTO = 19
    CREATE_TEXT = 20
    CREATE_QUOTE = 21
    CREATE_LINK = 22
    CREATE_CHAT = 23
    CREATE_AUDIO = 24
    CREATE_VIDEO = 25
    REBLOG = 26
    DELETE_POST = 27
    EDIT_POST = 28
    NOTES = 29


class Call(DB_Base):
    __tablename__ = "calls"
    __mapper_args__ = {"eager_defaults": True}

    id = Column(Integer, primary_key=True)
    time = Column(DateTime)
    call = Column(Enum(CallFunc))
    limit = Column(Integer)
    duration = Column(Integer)
