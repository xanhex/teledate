"""Database tests."""
import asyncio
import datetime

import pytest

from teledate.app import database as db


@pytest.fixture(scope='module')
def event_loop():
    """Fix pytest async module error."""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def db_init():
    """Fixture for creating database."""
    async with db.async_engine.begin() as conn:
        await conn.run_sync(db.Base.metadata.drop_all)
        await conn.run_sync(db.Base.metadata.create_all)


@pytest.fixture()
async def user() -> dict:
    """Fixture for creating the test user entry."""
    async with db.async_session() as session:
        async with session.begin():
            user = db.User(name='tester')
            session.add(user)
    return {
        'id': 1,
        'name': 'tester',
        'activity': 'Default',
    }


@pytest.fixture()
async def record(user: dict) -> dict:
    """Fixture for creating the test user entry."""
    async with db.async_session() as session:
        async with session.begin():
            record = db.Record(user_id=user['id'])
            session.add(record)
        date = await record.awaitable_attrs.date
    return {
        'id': 1,
        'date': date,
        'user_id': 1,
    }


# User tests


async def test_create_user():
    """Test creating user with valid username."""
    user_id, user_activity = await db.create_user('Tester1 2')
    assert (user_id, user_activity) == (1, 'Default')


async def test_cant_create_user_invalid_username():
    """Test creating user with invalid username."""
    user_id, user_activity = await db.create_user('Tester.1"')
    assert (user_id, user_activity) == (None, None)


async def test_create_user_valid_activity():
    """Test creating user with valid activity."""
    user_id, user_activity = await db.create_user('Tester', 'Activity 1')
    assert (user_id, user_activity) == (1, 'Activity 1')


async def test_cant_create_user_invalid_activity():
    """Test creating user with invalid activity."""
    user_id, user_activity = await db.create_user('Tester', 'Activity.1!')
    assert (user_id, user_activity) == (None, None)


async def test_get_user_info(user: dict):
    """Test getting existing user info."""
    user_id, user_activity = await db.get_user_info(user['name'])
    assert (user_id, user_activity) == (user['id'], user['activity'])


async def test_get_nonexistent_user_info():
    """Test getting non-existent user info."""
    user_id, user_activity = await db.get_user_info('tester')
    assert (user_id, user_activity) == (None, None)


async def test_get_user_count(user: dict):
    """Test getting user count."""
    user_count = await db.get_user_count()
    assert user_count == 1


# Record tests


async def test_create_record(user: dict):
    """Test creating record of existing user."""
    record_date = await db.create_record(user['id'])
    assert isinstance(record_date, datetime.datetime)


async def test_cant_create_record_nonexistent_user():
    """Test creating record of non-existent user."""
    record_date = await db.create_record(1)
    assert record_date is None


async def test_create_record_valid_dates(user: dict):
    """Test creating record with valid dates."""
    record_date = await db.create_record(user['id'], None)
    assert isinstance(record_date, datetime.datetime)
    dt = datetime.datetime(2000, 1, 1)
    record_date = await db.create_record(user['id'], dt)
    assert record_date == dt


async def test_cant_create_records_invalid_dates(user: dict):
    """Test creating record with invalid date."""
    record_date = await db.create_record(user['id'], 'Not dt')
    assert record_date is None
    record_date = await db.create_record(user['id'], '')
    assert record_date is None


async def test_get_all_records(record: dict):
    """Test getting all records."""
    records_dates: list = await db.get_all_records()
    assert records_dates[0] == record['date']


async def test_get_user_records(record: dict):
    """Test getting user records."""
    records_dates: list = await db.get_user_records(record['user_id'])
    assert records_dates[0] == record['date']
    records_dates: list = await db.get_user_records(2)
    assert not records_dates


async def test_get_last_user_record(record: dict):
    """Test getting last user record."""
    record_date = await db.get_last_user_record(record['user_id'])
    assert record_date == record['date']
    record_date = await db.get_last_user_record(2)
    assert not record_date


# User and Record tests


async def test_delete_user_cascade_records(record: dict):
    """Test getting last user record."""
    assert await db.get_all_records()
    assert await db.delete_user(record['user_id']) is True
    assert not await db.get_all_records()


async def test_delete_user_nonexistent():
    """Test deleting nonexistent user."""
    user_count = await db.get_user_count()
    assert user_count == 0
    assert await db.delete_user(1) is False


async def test_delete_records_nonexistent_user():
    """Test deleting records of nonexistent user."""
    assert await db.delete_records(1) is False
