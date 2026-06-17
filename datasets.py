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
    ("JIRA_AUDIT_ALL_DATASET_ID", "jira_audit_all"),
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

    def create_jira_audit_view(self):
        query = """
            WITH mapping AS (
                SELECT
                    issue_key,
                    parent_key,
                    "Audit type_value",
                    "Plan End Date(WBSGantt)",
                    "Plan Start Date(WBSGantt)",
                    "Release Date",
                    Resolved
                FROM jira_audit_all
            )
            SELECT
                a.issue_key AS subtask_key,
                a.parent_key,
                a.priority_name AS priority,
                a.status_name AS status,
                COALESCE(a."Audit type_value", m."Audit type_value") AS audit_type,
                a.resolution_name AS resolution,
                a.reporter_displayName AS auditor,
                a.assignee_displayName AS assignee,
                a."Issue Type" AS issue_type,
                a.Labels AS labels,
                a.Summary AS summary,
                COALESCE(DATE(a."Plan End Date(WBSGantt)"), DATE(m."Plan End Date(WBSGantt)")) AS plan_end_date,
                COALESCE(DATE(a."Plan Start Date(WBSGantt)"), DATE(m."Plan Start Date(WBSGantt)")) AS plan_start_date,
                DATE(a."Fix deadline") AS fix_deadline_date,
                COALESCE(DATE(a."Release Date"), DATE(m."Release Date")) AS release_date,
                COALESCE(DATE(a.Resolved), DATE(m.Resolved)) AS resolved_date,
                DATE(a.Updated) AS updated_date,
                DATE(a.Created) AS created_date
            FROM jira_audit_all a
            LEFT JOIN mapping m ON a.parent_key = m.issue_key
            WHERE (a.parent_key NOT IN ('AUDIT-19171','AUDIT-81904','EXTAUDIT-8749') OR a.parent_key IS NULL)
            AND a."Issue Type" IN ('Vulnerability')
        """
        with sqlite3.connect(self.DB_PATH) as connect:
            df = pd.read_sql_query(query, connect)
            df.to_sql("jira_audit_filtered", connect, if_exists="replace", index=False)
            logger.info(f"Created table 'jira_audit_filtered' with {len(df)} rows.")


def main():
    setup_logging()
    domo_datasets = DOMODatasets()
    domo_datasets.oss_database(domo_datasets.load_datasets())
    domo_datasets.create_jira_audit_view()
    table_names = ", ".join(table_name for _, table_name in DATASET_CONFIG)
    logger.info(f"Exported tables ({table_names}).")


if __name__ == "__main__":
    main()
