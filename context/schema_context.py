from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "database" / "oss_database.db"

OPEN_STATUS_VULNERABILITY = (
    "Open",
    "Reopened",
    "Pending",
    "In Progress"
)

CLOSED_STATUS_VULNERABILITY = (
    "Closed",
    "Resolved"
)

ISSUE_TYPES = (
    "Security Audit",
    "Vulnerability"
)

AUDIT_TYPES = (
    "Pre-release",
    "Regular"
)

RESOLUTIONS = (
    "Fixed",
    "Answered",
    "Risk Accepted"
)

DATE_FORMAT = "YYYY-MM-DD HH:MM:SS"

SQL_RULES = (
    "Use jira_audit_filtered as the main table for all queries. If you think you need more details about the user question, you can query other tables and join with jira_audit_filtered.subtask_key = overall_vulnerability.ticket_key.",
    "Only SELECT statements. Never INSERT, UPDATE, DELETE, DROP, or ALTER.",
    "Date columns are TEXT. Format: YYYY-MM-DD HH:MM:SS.",
    "There are columns with NULL values. Handle them appropriately in your queries.",
    "Use overall_vulnerability table when looking for organization details of the audit tickets, such as which department is responsible for the ticket, which team is responsible for the ticket, etc. Always join with jira_audit_filtered to get the ticket details.",
    "Always include LIMIT 500 on queries that return rows.",
)

TableName = Literal["overall_vulnerability", "jira_audit_filtered"]

@dataclass(frozen=True)
class ColumnDef:
    name: str
    type: str
    description: str
    quoted: bool = False

    @property
    def sql_name(self) -> str:
        return f'"{self.name}"' if self.quoted else self.name


@dataclass(frozen=True)
class TableDef:
    name: TableName
    purpose: str
    use_when: str
    columns: tuple[ColumnDef, ...]


JIRA_AUDIT_FILTERED = TableDef(
    name="jira_audit_filtered",
    purpose="Contains detailed information about Jira tickets related to audit tickets, including their status, priority, audit type, resolution, reporter, assignee, issue type, labels, summary, and various date fields.",
    use_when=(
        "Use this table for any analysis about audit tickets when user asks about KPIs related to audit tickets, "
        "when user want to ask about individual performance of an individual auditor, "
        "when user want to know statistics about the audit tickets such as how many open/closed tickets, "
        "how many tickets of each priority, etc."
    ),
    columns=(
        ColumnDef(name="subtask_key", type="TEXT", description="The unique identifier for the Jira subtask."),
        ColumnDef(name="parent_key", type="TEXT", description="The unique identifier for the parent Jira issue."),
        ColumnDef(name="priority", type="TEXT", description="The priority level of the Jira issue. This is the heirarchy of priority: Blocker > Critical > Major > Minor > Trivial."),
        ColumnDef(name="status", type="TEXT", description="The current status of the Jira issue."),
        ColumnDef(name="audit_type", type="TEXT", description="The type of audit, either 'Pre-release' or 'Regular'."),
        ColumnDef(name="resolution", type="TEXT", description="How the ticket was resolved or closed."),
        ColumnDef(name="auditor", type="TEXT", description="The auditor who's responsible for the jira issue."),
        ColumnDef(name="assignee", type="TEXT", description="The one who assign the jira issue to the auditor."),
        ColumnDef(name="issue_type", type="TEXT", description="Usually we only have one issue type which is 'Vulnerability' because we focus on vulnerabilities."),
        ColumnDef(name="labels", type="TEXT", description="Any labels associated with the Jira issue."),
        ColumnDef(name="summary", type="TEXT", description="Title of the Jira issue."),
        ColumnDef(name="plan_end_date", type="TEXT", description=f"The planned end date for the audit task. Format: {DATE_FORMAT}."),
        ColumnDef(name="plan_start_date", type="TEXT", description=f"The planned start date for the audit task. Format: {DATE_FORMAT}."),
        ColumnDef(name="fix_deadline_date", type="TEXT", description=f"The deadline for fixing the vulnerability when the resolution is 'Risk Accepted'. Format: {DATE_FORMAT}."),
        ColumnDef(name="release_date", type="TEXT", description=f"The release date of the software release. Format: {DATE_FORMAT}."),
        ColumnDef(name="resolved_date", type="TEXT", description=f"The date when the Jira issue was risk accepted or closed. Format: {DATE_FORMAT}."),
        ColumnDef(name="updated_date", type="TEXT", description=f"The date when the Jira issue was last updated. Format: {DATE_FORMAT}."),
        ColumnDef(name="created_date", type="TEXT", description=f"The date when the Jira issue was created. Format: {DATE_FORMAT}.")
    )
)

OVERALL_VULNERABILITY = TableDef(
    name="overall_vulnerability",
    purpose="Vulnerability tickets with org hierarchy, resolution metrics, and MTTR.",
    use_when=(
        "Default table for backlog counts, resolution rates, MTTR, "
        "priority/audit-type breakdowns, and org/service rollups."
    ),
    columns=(
        ColumnDef("ticket_key", "TEXT", "Vulnerability ticket key, this tickets has parent ticket."),
        ColumnDef("parent_key", "TEXT", "Parent ticket key, this is where the vulnerability ticket belongs."),
        ColumnDef("reporter", "TEXT", "The auditor responsible for the jira audit ticket."),
        ColumnDef("type", "TEXT", 'Ticket type.'),
        ColumnDef("status", "TEXT", "Current JIRA issue status."),
        ColumnDef("priority", "TEXT", "Priority level (Blocker > Critical > Major > Minor > Trivial)."),
        ColumnDef("resolution", "TEXT", "How the ticket was resolved or closed."),
        ColumnDef("audit_type", "TEXT", "The type of audit associated with the ticket."),
        ColumnDef("created_date", "TEXT", f"Ticket created. Format: {DATE_FORMAT}."),
        ColumnDef("release_date", "TEXT", "Planned release date."),
        ColumnDef("plan_end_date", "TEXT", "Planned end date."),
        ColumnDef("resolution_date", "TEXT", "When resolved. Empty if still open."),
        ColumnDef("closed_date", "TEXT", "When fully closed."),
        ColumnDef("resolved_date", "TEXT", "Alternate resolved timestamp."),
        ColumnDef("fix_deadline", "TEXT", "Target fix deadline."),
        ColumnDef("isFixWithinDeadline", "TEXT", "Whether fix was within deadline."),
        ColumnDef("mttrToFixed", "REAL", "Mean time to resolve to fixed in days."),
        ColumnDef("mttrToRiskAccepted", "REAL", "Mean time to resolve to risk accepted in days."),
        ColumnDef("year", "INTEGER", "Year extracted from created_date."),
        ColumnDef("month", "TEXT", "Month name (January, February, ...)."),
        ColumnDef("quarter_of_year", "INTEGER", "Quarter 1–4."),
        ColumnDef("week_of_year", "INTEGER", "Week 1–52."),
        ColumnDef("org_name", "TEXT", "Owning organization or team."),
        ColumnDef("service_name", "TEXT", "Service or application name."),
        ColumnDef("l0_org_name", "TEXT", "Top-level org (broadest)."),
        ColumnDef("l1_org_name", "TEXT", "Org hierarchy level 1."),
        ColumnDef("l2_org_name", "TEXT", "Org hierarchy level 2."),
        ColumnDef("l3_org_name", "TEXT", "Org hierarchy level 3."),
        ColumnDef("l4_org_name", "TEXT", "Org hierarchy level 4."),
        ColumnDef("l5_org_name", "TEXT", "Org hierarchy level 5 (most granular)."),
    ),
)

DATASET_CONFIG: tuple[tuple[str, TableDef], ...] = (
    ("jira_audit_filtered", JIRA_AUDIT_FILTERED),
    ("overall_vulnerability", OVERALL_VULNERABILITY)
)


def format_enum(title: str, values: tuple[str, ...]) -> str:
    return f"{title}: {', '.join(values)}"


def format_table(table_def: TableDef) -> str:
    line = [
        f"Table: {table_def.name}",
        f"Purpose: {table_def.purpose}",
        f"Use when: {table_def.use_when}",
        "Columns:",
    ]
    for column in table_def.columns:
        line.append(f"  - {column.name} ({column.type}): {column.description}")
    return "\n".join(line)


def build_schema_prompt() -> str:
    """Build the schema context string for the LLM system prompt."""
    sections = [
        "# Database Schema Context",
        "",
            "You analyze audit tickets data from a local SQLite database.",
            "Generate read-only SELECT queries only.",
            "The main table is jira_audit_filtered, which contains detailed information about Jira tickets related to audit tickets, including their status, priority, audit type, resolution, reporter, assignee, issue type, labels, summary, and various date fields. But if you need to answer user question about organization details of the audit tickets, such as which department is responsible for the ticket, which team is responsible for the ticket, etc., you can use overall_vulnerability table and always join with jira_audit_filtered to get the ticket details.",
        "",
        "## SQL Rules",
        *[f"- {rule}" for rule in SQL_RULES],
        "",
        "## Business Definitions",
        format_enum("Open ticket statuses", OPEN_STATUS_VULNERABILITY),
        format_enum("Closed ticket statuses", CLOSED_STATUS_VULNERABILITY),
        format_enum("Issue ticket types", ISSUE_TYPES),
        format_enum("Audit types", AUDIT_TYPES),
        format_enum("Resolutions of audit tickets", RESOLUTIONS),
        "",
        "## Tables",
        "",
        format_table(JIRA_AUDIT_FILTERED),
        "",
        format_table(OVERALL_VULNERABILITY)
    ]

    return "\n".join(sections)

SCHEMA_CONTEXT = build_schema_prompt()

if __name__ == "__main__":
    print(SCHEMA_CONTEXT)