"""Database with SQLAlchemy utilities."""

import logging
import sys
from contextlib import contextmanager
from multiprocessing.util import register_after_fork
from typing import List, Literal, Optional, Union

import pandas as pd
from sqlacodegen.generators import DeclarativeGenerator
from sqlalchemy import MetaData, Table, create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from db_config.configuration import db_url
from db_config.db_exceptions import DBError

__sh = logging.StreamHandler(sys.stdout)
__formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s | %(funcName)s: %(message)s")
__sh.setFormatter(__formatter)

_logger = logging.getLogger("__database__")
_logger.setLevel("INFO")
_logger.addHandler(__sh)

logger = logging.getLogger(__name__)


class DBConnection:
    def __init__(self, url: str = db_url):
        self.engine = create_engine(
            url=url,
            pool_pre_ping=True,
            max_overflow=5,
            pool_size=3,
            pool_recycle=90,
        )
        register_after_fork(self.engine, self.engine.dispose)
        self._session = sessionmaker(bind=self.engine)

    @contextmanager
    def session(self):
        """Yields SQLAlchemy Session for ORM."""
        __session = self._session()

        try:
            yield __session
            __session.commit()

        except SQLAlchemyError as e:
            __session.rollback()
            _logger.error(f"Session transaction failed: {e}")
            raise DBError(str(e))

        except Exception as e:
            __session.rollback()
            _logger.error(f"Session transaction failed: {e}")
            raise
        finally:
            __session.close()

    def generate_data_models(self, schema: str) -> None:
        """Prints generated data models output from sqlacodegen."""
        metadata = MetaData(self.engine)
        metadata.reflect(self.engine, schema, False, None)

        generator = DeclarativeGenerator(metadata, self.engine, ())
        print(generator.generate())  # noqa

    def save_df(
        self,
        df: pd.DataFrame,
        schema_name: str,
        table_name: str,
        to_sql_options: dict = {
            "if_exists": "append",
            "index": False,
            "chunksize": 3000,
            "method": "multi",
        },
    ) -> None:
        """Save DataFrame into database.

        Args:
            df (pd.DataFrame): Dataframe to save.
            schema_name (str): Schema name.
            table_name (str): Table name.
            to_sql_options: Optional kwargs for DataFrame.to_sql. Refer to
                https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_sql.html

        """
        df.to_sql(con=self.engine, schema=schema_name, name=table_name, **to_sql_options)

    def load_df(
        self,
        table_class,
        filter_by: dict = None,
        filter_exp: List = None,
        count: bool = False,
    ) -> pd.DataFrame:
        """Load DataFrame from database query.

        Args:
            table_class: Class in `data_models`.
            filter_by (dict, optional): Dictionary to filter the query to pass to
                the `filter_by` in query. Key in dictionary corresponds to
                column name in table.
            filter_exp (List, optional): Expression to filter the query by `filter`.
            count (bool, optional): Return count of query instead of DataFrame. Default False.

        Returns:
            pd.DataFrame: Queried data as dataframe.
        """
        with self.session() as __session:
            result_query = __session.query(table_class)

            if filter_by is not None:
                result_query = result_query.filter_by(**filter_by)

            if filter_exp is not None:
                result_query = result_query.filter(*filter_exp)

            if count:
                return result_query.count()

            return pd.read_sql(result_query.statement, result_query.session.bind)

    def _insert(
        self,
        values: List[dict],
        table: Table,
        returning: Optional[List[str]] = None,
        on_conflict: Literal["fail", "do_nothing", "do_update"] = "fail",
        on_conflict_kwargs: Optional[dict] = None,
    ):
        """Inserts data to database, supports "upsert" and "returning" generated column values."""
        stmt = postgresql.insert(table).values(values)

        if returning:
            stmt = stmt.returning(*[table.c[r] for r in returning])

        if on_conflict_kwargs is None:
            on_conflict_kwargs = {}

        if on_conflict == "do_nothing":
            stmt = stmt.on_conflict_do_nothing(**on_conflict_kwargs)
        elif on_conflict == "do_update":
            if "set_" not in on_conflict_kwargs:
                on_conflict_kwargs["set_"] = {e.key: e for e in stmt.excluded}

            stmt = stmt.on_conflict_do_update(**on_conflict_kwargs)

        if returning:
            return self.engine.execute(stmt).mappings().all()

        return self.engine.execute(stmt)

    def insert_data(
        self,
        data: Union[pd.DataFrame, dict, List[dict]],
        schema: str,
        table: str,
        returning: Optional[List[str]] = None,
        on_conflict: Literal["fail", "do_nothing", "do_update"] = "fail",
        on_conflict_kwargs: Optional[dict] = None,
        chunksize: Optional[int] = None,
    ) -> Optional[List[dict]]:
        """Inserts data to database, supports "upsert" and "returning" generated column values.

        Args:
            data (Union[pd.DataFrame, dict, List[dict]]): Data to be inserted into the database.
            schema (str): Schema under the database to insert into.
            table (str): Table under the schema to insert into.
            returning (Optional[List[str]]): List of column names to return values after insert
                execution.
            on_conflict (Literal["fail", "do_nothing", "do_update"]): In case of:
                - "fail": Raise error if there is conflict.
                - "do_nothing": Ignore row and skip insertion if there is conflict.
                - "do_update": Update row.
            on_conflict_kwargs (Optional[dict]): Options to pass into on_conflict methods. Note:
                - Only either "index_elements" or "constraint" should be passed, not both.
                - "index_elements" is list of column names to check for conflict.
                - "constraint" is constraint name to check for conflict.
                - "set_" is not necessary, by default all excluded columns will be updated.
            chunksize (Optional[int]): Specify the number of rows in each batch
            to be written at a time.
                By default, all rows will be written at once.

        Returns:
            Optional[List[dict]]: For statements with returning, this will be a records-like list of
                dicts keyed by columns specified in `returning`.
        """
        if isinstance(data, pd.DataFrame):
            data = data.to_dict("records")
        elif isinstance(data, dict):
            data = [data]

        metadata = MetaData(bind=self.engine, schema=schema)
        _table = Table(table, metadata, autoload=True)

        nrows = len(data)

        if chunksize is None:
            chunksize = nrows
        elif chunksize == 0:
            raise ValueError("chunksize argument should be non-zero")

        returned = []

        chunks = (nrows // chunksize) + 1
        if nrows % chunksize == 0:
            chunks -= 1

        for i in range(chunks):
            start_i = i * chunksize
            end_i = min((i + 1) * chunksize, nrows)
            _values = data[start_i:end_i]

            res = self._insert(_values, _table, returning, on_conflict, on_conflict_kwargs)

            if returning:
                returned += res

            logger.info(f"[{i + 1}/{chunks}] Inserted {len(_values)} rows.")

        if returning:
            return returned


# LEGACY SUPPORT FUNCTIONS
# WHEN CREATING NEW LOGIC, PLEASE USE THE METHODS DIRECTLY FROM DBConnection.
# IF SOMETHING SPECIFIC NEEDED, PLEASE INHERIT DB CONNECTION AND ADD NEW METHODS.
defaut_db = DBConnection()
engine = defaut_db.engine
_session = defaut_db._session


def generate_data_models(schema: str) -> None:
    """Prints generated data models output from sqlacodegen."""
    defaut_db.generate_data_models(schema)


def session() -> None:
    """Legacy support for session."""
    return defaut_db.session()


def save_df(
    df: pd.DataFrame,
    schema_name: str,
    table_name: str,
    to_sql_options: dict = {
        "if_exists": "append",
        "index": False,
        "chunksize": 3000,
        "method": "multi",
    },
) -> None:
    """Legacy support for DF saving."""
    defaut_db.save_df(df, schema_name, table_name, to_sql_options)


def load_df(
    table_class, filter_by: dict = None, filter_exp: List = None, count: bool = False
) -> pd.DataFrame:
    """Legacy support for DF loading."""
    return defaut_db.load_df(
        table_class=table_class, filter_by=filter_by, filter_exp=filter_exp, count=count
    )


def _insert(
    values: List[dict],
    table: Table,
    returning: Optional[List[str]] = None,
    on_conflict: Literal["fail", "do_nothing", "do_update"] = "fail",
    on_conflict_kwargs: Optional[dict] = None,
):
    """Legacy support for inserting data."""
    return defaut_db._insert(
        values=values,
        table=table,
        returning=returning,
        on_conflict=on_conflict,
        on_conflict_kwargs=on_conflict_kwargs,
    )


def insert_data(
    data: Union[pd.DataFrame, dict, List[dict]],
    schema: str,
    table: str,
    returning: Optional[List[str]] = None,
    on_conflict: Literal["fail", "do_nothing", "do_update"] = "fail",
    on_conflict_kwargs: Optional[dict] = None,
    chunksize: Optional[int] = None,
) -> Optional[List[dict]]:
    """Legacy support for inserting data."""
    return defaut_db.insert_data(
        data=data,
        schema=schema,
        table=table,
        returning=returning,
        on_conflict=on_conflict,
        on_conflict_kwargs=on_conflict_kwargs,
        chunksize=chunksize,
    )
