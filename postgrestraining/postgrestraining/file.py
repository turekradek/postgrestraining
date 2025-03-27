import logging
from datetime import datetime
import sqlalchemy
import pandas as pd

# import webscraping_mview_refresh.webscraping_utils.utils.configuration as config
import zz_deepscraping_test.deepscraping_utils.utils.configuration as config

from ers.db import DBConnection

DATE_STR_FORMAT = '%Y-%m-%d'
TIME_STR_FORMAT = '%Y-%m-%d %H:%M:%S'

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s | %(funcName)s: %(message)s",
)
logger = logging.getLogger(__name__)


def check_query():

    check_status = open(config.check_query_sql).read()
    sql_query = sqlalchemy.text(check_status)
    start_time = datetime.now()
    with DBConnection().session() as db_engine:
        try:
            results = db_engine.execute(sql_query)
            print(f'results ')
            print(results)
            # Convert the results to a Pandas DataFrame
            df = pd.DataFrame(results.fetchall(), columns=results.keys())

            # Print the DataFrame
            print(df)
            elapsed = datetime.now() - start_time
            print(f"daily_view started at: {start_time} Took: {elapsed}")
        except Exception as e:
            print(e)