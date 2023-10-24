"""Database settings and services."""
import asyncio

from decouple import config
from sqlalchemy import DateTime, ForeignKey, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import (
    Mapped,
    declarative_base,
    mapped_column,
    relationship,
    sessionmaker,
)

DB_URL = config('MYSQL_URL', default='sqlite+aiosqlite:///data.db')
USER_LIMIT = 2
RECORD_LIMIT = 15

engine = create_async_engine(DB_URL)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    autocommit=False,
    expire_on_commit=False,
)

Base = declarative_base()


class User(Base):
    """Model for the male nickname."""

    __tablename__ = 'user'
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(unique=True, index=True)
    records: Mapped[list['Record']] = relationship(
        back_populates='user',
        cascade='all, delete',
    )

    def __repr__(self) -> str:
        """To representation."""
        return self.name


class Record(Base):
    """Model for the female nickname."""

    __tablename__ = 'record'
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    date = mapped_column(
        DateTime(),
        server_default=func.now(),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    user: Mapped[User] = relationship('User', back_populates='records')

    def __repr__(self) -> str:
        """To representation."""
        return self.date.strftime('%d/%m/%Y %H:%M:%S')


async def init_models() -> None:
    """Create all tables on app startup."""
    async with engine.begin() as conn:
        # To clear DB before re-creating it
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


# CRUD


async def get_user(username: str) -> Mapped[User] | None:
    """Read user from DB."""
    async with async_session() as session:
        async with session.begin():
            return await session.scalar(
                select(User).where(User.name == username),
            )


async def get_user_count() -> int:
    """Read user from DB."""
    async with async_session() as session:
        async with session.begin():
            return await session.scalar(
                select(func.count()).select_from(User),
            )


async def create_user(username: str) -> Mapped[User] | str:
    """Read user from DB."""
    async with async_session() as session:
        async with session.begin():
            user = User(
                name=username,
            )
            session.add(user)
            try:
                await session.commit()
                return user
            except IntegrityError:
                await session.rollback()
                return f'User {username} already exists!'


async def get_last_user_record(username: str) -> Mapped[Record]:
    """Read user from DB."""
    async with async_session() as session:
        async with session.begin():
            records = await session.scalars(
                select(Record)
                .join(User)
                .where(User.name == username)
                .order_by(Record.id.desc()),
            )
            return records.first()


async def get_user_records(username: str) -> list[Mapped[Record]]:
    """Read user from DB."""
    async with async_session() as session:
        async with session.begin():
            return await session.scalars(
                select(Record).join(User).where(User.name == username),
            )


async def get_all_records() -> list[Mapped[Record]]:
    """Read user from DB."""
    async with async_session() as session:
        async with session.begin():
            return await session.scalars(select(Record))


async def create_record(username: str) -> Mapped[User] | str:
    """Read user from DB."""
    async with async_session() as session:
        async with session.begin():
            user = await get_user(username)
            if not user:
                return f'User {username} does not exist!'
            record = Record(
                user_id=user.id,
            )
            session.add(record)
            try:
                await session.commit()
                return record
            except IntegrityError:
                await session.rollback()
                return 'Record with such date already exists!'


async def delete_user(username: str) -> bool | str:
    """Read user from DB."""
    async with async_session() as session:
        async with session.begin():
            user = await get_user(username)
            if not user:
                return f'User {username} does not exist!'
            try:
                await session.delete(user)
                return True
            except IntegrityError as err:
                await session.rollback()
                return err


if __name__ == '__main__':
    asyncio.run(init_models())
    # user = asyncio.run(create_user('Bruno'))
    # print(type(user))
    # asyncio.run(create_user('Mars'))
    # records = asyncio.run(get_records('Mars'))
    # records = asyncio.run(get_records('New'))
    # print(*records)
