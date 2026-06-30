from client import DomoClass
from dotenv import load_dotenv
from logger import setup_logging, get_logger
import pandas as pd
import sqlite3
import os
import io

logger = get_logger(__name__)
load_dotenv()

DATASET_CONFIG = [
    ("OVERALL_VULNERABILITY_DATASET_ID", "overall_vulnerability"),
]


class DOMODatasets:
    DB_PATH = os.path.join(os.path.dirname(__file__), "database/oss_database.db")

    def __init__(self):
        self.domo_client = DomoClass().get_domo_client()

    def get_dataset(self, dataset_id: str):
        try:
            get_dataset = self.domo_client.datasets.data_export(dataset_id, include_csv_header=True)
        except Exception as e:
            logger.error(f"Error fetching domo dataset for {dataset_id}: {e}")
            raise
        return get_dataset

    def fetch_dataset(self, env_key: str) -> pd.DataFrame:
        dataset_id = os.getenv(env_key)
        dataset = self.get_dataset(dataset_id)
        return pd.read_csv(io.StringIO(dataset), low_memory=False)

    def load_datasets(self) -> list[tuple[pd.DataFrame, str]]:
        datasets = []
        for env_key, table_name in DATASET_CONFIG:
            try:
                df = self.fetch_dataset(env_key)
                datasets.append((df, table_name))
            except Exception as e:
                logger.error(f"Error fetching dataset for {env_key}: {e}")
        return datasets

    def oss_database(self, datasets: list[tuple[pd.DataFrame, str]]) -> str:
        with sqlite3.connect(self.DB_PATH) as connect:
            for df, table_name in datasets:
                df.to_sql(table_name, connect, if_exists="replace", index=False)


def main():
    setup_logging()
    domo_datasets = DOMODatasets()
    domo_datasets.oss_database(domo_datasets.load_datasets())
    table_names = ", ".join(table_name for _, table_name in DATASET_CONFIG)
    logger.info(f"Exported tables ({table_names}).")


if __name__ == "__main__":
    main()
