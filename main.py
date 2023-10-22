# import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text
from decouple import config

DB_URL = config('MYSQL_URL', default='sqlite+pysqlite:///:memory:')

engine = create_engine(DB_URL)
with engine.connect() as conn:
    result = conn.execute(text("select 'hello world'"))
    print(result.all())

# fig, ax = plt.subplots()
# ax.plot(['01.01.23', '02.01.23', '04.01.23', '06.01.23', '08.01.23', '10.01.23'], [48, 49, 58, 28, 43, 48], marker='o')
# ax.set_ylabel('Hours')
# ax.set_xlabel('Date')
# plt.savefig('foo.png')