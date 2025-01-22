from sqlalchemy import create_engine
import pandas as pd
import configparser
from . import sql_queries
from typing import Dict
from logger_config import LogConfig
from decouple import config
from datetime import datetime, timezone
import time

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
                max_overflow=2,
                pool_timeout=60,
                pool_pre_ping=True,
                pool_recycle=3600
            )
        return self._engine

    def fetch_data(self) -> pd.DataFrame:
        """Fetch data with simple connection"""
        engine = self._get_engine()
        start_time = time.time()
        logger.info("Starting make ready data refresh from database...")

        try:
            df = pd.read_sql(sql_queries.MAKE_READY_QUERY, engine)
            execution_time = time.time() - start_time
            logger.info(
                f"Make ready data refresh completed in {execution_time:.2f} seconds. Retrieved {len(df)} records.")
            return df
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Make ready data refresh failed after {execution_time:.2f} seconds. Error: {str(e)}")
            raise

    async def fetch_version_info(self, query: str) -> Dict:
        """Fetch version information from database"""
        try:
            engine = self._get_engine()
            logger.debug(f"Executing version check query")
            df = pd.read_sql(query, engine)
            logger.debug(f"Query result: {df.to_dict()}")

            if not df.empty:
                last_modified = df['last_modified'].iloc[0]
                logger.debug(f"Last modified raw value: {last_modified}, type: {type(last_modified)}")

                if pd.notnull(last_modified):
                    # Convert to datetime if it's not already
                    if not isinstance(last_modified, datetime):
                        if isinstance(last_modified, pd.Timestamp):
                            last_modified = last_modified.to_pydatetime()
                        else:
                            # If it's a date, convert to datetime at midnight UTC
                            last_modified = datetime.combine(last_modified, datetime.min.time())

                    # Ensure UTC timezone
                    if last_modified.tzinfo is None:
                        last_modified = last_modified.astimezone(timezone.utc)

                    logger.debug(f"Final last_modified with timezone: {last_modified}")

                result = {
                    'last_modified': last_modified,
                    'record_count': int(df['record_count'].iloc[0])
                }
                logger.debug(f"Returning version info: {result}")
                return result

            logger.warning("Query returned empty DataFrame")
            return None
        except Exception as e:
            logger.error(f"Error fetching version info: {str(e)}", exc_info=True)
            return None

    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute a SQL query and return results"""
        engine = self._get_engine()
        return pd.read_sql(query, engine)
