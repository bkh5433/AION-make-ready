from sqlalchemy import create_engine
import pandas as pd
import configparser
from . import sql_queries
from typing import Dict
from logger_config import LogConfig
from decouple import config

logger_config = LogConfig()
logger = logger_config.get_logger('db_connection')


class DatabaseConnection:
    """Simple database connection for daily data refresh"""

    def __init__(self):
        self._engine = None

    def _get_engine(self):
        """Create engine only when needed"""
        if not self._engine:
            connection_url = (
                f"mssql+pyodbc://{config('DB_USER')}:"
                f"{config('DB_PASSWORD')}@"
                f"{config('DB_SERVER')}/"
                f"{config('DB_NAME')}?"
                f"driver=ODBC+Driver+18+for+SQL+Server&"
                f"TrustServerCertificate=yes"
            )

            self._engine = create_engine(
                connection_url,
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

    async def fetch_version_info(self, query: str) -> Dict:
        """Fetch version information from database"""
        try:
            engine = self._get_engine()
            df = pd.read_sql(query, engine)

            if not df.empty:
                return {
                    'last_modified': df['last_modified'].iloc[0].isoformat() if pd.notnull(
                        df['last_modified'].iloc[0]) else None,
                    'record_count': int(df['record_count'].iloc[0])
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching version info: {str(e)}")
            return None

    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute a SQL query and return results"""
        engine = self._get_engine()
        return pd.read_sql(query, engine)
