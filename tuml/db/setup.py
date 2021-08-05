import logging

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from db.tables import DB_Base, db_engine_ctx
from db.allowed_account import allow_account


async def init_db(cfg, admin_email):

    db_engine = create_async_engine(cfg['db']['url'], echo=True, hide_parameters=True)
    async with db_engine.begin() as conn_a:
        await conn_a.run_sync(DB_Base.metadata.drop_all)
        await conn_a.run_sync(DB_Base.metadata.create_all)

    db_session = sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    await allow_account(db_session, admin_email)
    logging.info('User [%s] succesfully added.', admin_email)

    await db_engine.dispose()
