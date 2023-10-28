"""Database settings and services."""
import asyncio
import datetime

from decouple import config
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    engine,
    func,
    select,
)
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
RECORDS_LIMIT = 30

async_engine = create_async_engine(DB_URL)


async_session = sessionmaker(
    async_engine,
    class_=AsyncSession,
    autocommit=False,
    expire_on_commit=False,
)

Base = declarative_base()


class User(Base):
    """User model."""

    __tablename__ = 'user_table'
    __table_args__ = (
        CheckConstraint(r"activity REGEXP '^([a-zA-Z]|\s|\d){1,50}$'"),
        CheckConstraint(r"name REGEXP '^([a-zA-Z]|\s|\d){1,50}$'"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    activity: Mapped[str] = mapped_column(String(50), default='Default')
    records: Mapped[list['Record']] = relationship(
        back_populates='user',
        cascade='all, delete',
    )

    def __repr__(self) -> str:
        """To representation."""
        return self.name


class Record(Base):
    """User record model."""

    __tablename__ = 'record_table'
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    date: Mapped[datetime.datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey('user_table.id'))
    user: Mapped[User] = relationship(
        back_populates='records',
        single_parent=True,
    )

    def __repr__(self) -> str:
        """To representation."""
        return self.date.strftime('%d.%m.%Y %H:%M:%S')


async def init_models() -> None:
    """Create all tables on app startup."""
    async with async_engine.begin() as conn:
        # To clear DB before re-creating it
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


# CRUD

async def get_user_info(username: str) -> tuple[int, str] | tuple[None]:
    """
    Get a user ID in the database.

    Returns:
        The user ID and the user activity name, None otherwise.
    """
    async with async_session() as session:
        async with session.begin():
            user: User = await session.scalar(
                select(User).where(User.name == username),
            )
            try:
                return user.id, user.activity
            except Exception:
                return None, None


async def get_user_count() -> int:
    """Get the number of users in the database."""
    async with async_session() as session:
        async with session.begin():
            return await session.scalar(
                select(func.count()).select_from(User),
            )


async def create_user(
    username: str,
    activity: str | None = None,
) -> tuple[int, str] | tuple[None]:
    """
    Create a user entry in the database.

    Returns:
        The user ID and the user activity name, None otherwise.
    """
    async with async_session() as session:
        async with session.begin():
            user = User(
                name=username,
                activity=activity,
            )
            session.add(user)
        try:
            await session.commit()
            return user.id, user.activity
        except Exception:
            await session.rollback()
            return None, None


async def get_last_user_record(user_id: int) -> datetime.datetime | None:
    """Get info on the last user's record in the database."""
    async with async_session() as session:
        async with session.begin():
            records: list[Record] = await session.scalars(
                select(Record)
                .where(Record.user_id == user_id)
                .order_by(Record.id.desc()),
            )
            try:
                return records.first().date
            except Exception:
                return None


async def get_user_records(user_id: int) -> list[datetime.datetime] | None:
    """Get the dates of the user's records in the database."""
    async with async_session() as session:
        async with session.begin():
            records: list[Record] = await session.scalars(
                select(Record).where(Record.user_id == user_id),
            )
            try:
                return [record.date for record in records]
            except Exception:
                return None


async def get_all_records() -> list[datetime.datetime] | None:
    """Get the dates of all records in the database."""
    async with async_session() as session:
        async with session.begin():
            records: list[Record] = await session.scalars(select(Record))
            try:
                return [record.date for record in records]
            except Exception:
                return None


async def create_record(
    user_id: int,
    date: datetime.datetime = None,
) -> datetime.datetime | None:
    """
    Create a user's record in the database.

    Returns:
        The user's record info, None otherwise.
    """
    async with async_session() as session:
        async with session.begin():
            if not await session.get(User, user_id):
                return None
            record = Record(
                user_id=user_id,
                date=date,
            )
            session.add(record)
            try:
                await session.commit()
                return record.date
            except Exception:
                await session.rollback()
                return None


async def delete_user(user_id: int) -> bool:
    """Delete a user from the database."""
    async with async_session() as session:
        async with session.begin():
            try:
                user = await session.get(User, user_id)
                await session.delete(user)
                return True
            except Exception:
                return False


async def delete_records(
    user_id: int,
    count: int = 15,
) -> bool:
    """Delete a number of records from the database."""
    async with async_session() as session:
        async with session.begin():
            records_sr: engine.result.ScalarResult = await session.scalars(
                select(Record).where(Record.user_id == user_id).limit(count),
            )
            records: list[Record] = records_sr.all()
            if not records:
                return False
            try:
                for record in records:
                    await session.delete(record)
                return True
            except Exception:
                await session.rollback()
                return False


if __name__ == '__main__':
    asyncio.run(init_models())
    # user, activity = asyncio.run(create_user('Mark', 'Marko   Polo12'))
    # asyncio.run(create_record(user))
    # print(asyncio.run(get_user_records(1)))
    # print(asyncio.run(delete_records(1)))
    # print(asyncio.run(get_user_records(1)))

    # print(asyncio.run(create_user('xanhex')))
    # print(asyncio.run(get_user_info('xanhex')))
    # print(asyncio.run(get_user_count()))
    # print(asyncio.run(get_all_records()))
    # print(asyncio.run(delete_user(1)))
    # print(asyncio.run(get_user_info('xanhex')))
    # print(asyncio.run(get_user_count()))
    # print(asyncio.run(get_all_records()))
