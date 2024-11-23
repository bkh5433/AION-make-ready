from sqlalchemy import create_engine
import pandas as pd
import configparser
from . import sql_queries


class DatabaseConnection:
    """Simple database connection for daily data refresh"""

    def __init__(self):
        self._engine = None

    def _get_engine(self):
        """Create engine only when needed"""
        if not self._engine:
            config = configparser.ConfigParser()
            config.read('config.ini')

            connection_url = (
                f"mssql+pyodbc://{config['DATABASE']['USER']}:"
                f"{config['DATABASE']['PASSWORD']}@"
                f"{config['DATABASE']['SERVER']}/"
                f"{config['DATABASE']['DATABASE']}?"
                f"driver=ODBC+Driver+18+for+SQL+Server&"
                f"TrustServerCertificate=yes"
            )

            self._engine = create_engine(
                connection_url,
                # Basic settings for single-use connection
                pool_size=1,
                max_overflow=0,
                pool_timeout=30,
                pool_pre_ping=True
            )
        return self._engine

    def fetch_data(self) -> pd.DataFrame:
        """Fetch data with simple connection"""
        engine = self._get_engine()
        return pd.read_sql(sql_queries.MAKE_READY_QUERY, engine)
