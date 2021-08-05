from sqlalchemy import Column
from sqlalchemy import Text
from sqlalchemy import DateTime
from sqlalchemy import Boolean
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.dialects.mysql import ENUM
from sqlalchemy.sql.expression import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker


DB_Base = declarative_base()


class AllowedAccount(DB_Base):
    __tablename__ = "allowed_accounts"
    __mapper_args__ = {"eager_defaults": True}

    uid = Column(BIGINT(unsigned=True), default=func.uuid_short(), primary_key=True)
    email = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False)


class User(DB_Base):
    __tablename__ = "users"
    __mapper_args__ = {"eager_defaults": True}

    uid = Column(BIGINT(unsigned=True), default=func.uuid_short(), primary_key=True)
    email = Column(Text, nullable=False)
    given_name = Column(Text, nullable=True)
    family_name = Column(Text, nullable=True)
    name = Column(Text, nullable=True)
    avatar = Column(Text, nullable=True)


class Token(DB_Base):
    __tablename__ = "tokens"
    __mapper_args__ = {"eager_defaults": True}

    uid = Column(BIGINT(unsigned=True), default=func.uuid_short(), primary_key=True)
    token_type = Column(ENUM('nonce', 'state', 'access', 'grant'), nullable=False)
    created_at = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=False)
    is_active = Column(Boolean, nullable=False)


async def db_engine_ctx(app):

    app['db_engine'] = create_async_engine(app['cfg']['db']['url'], echo=True, hide_parameters=True)
    app['db_session'] = sessionmaker(app['db_engine'], expire_on_commit=False, class_=AsyncSession)

    yield

    await app['db_engine'].dispose()
