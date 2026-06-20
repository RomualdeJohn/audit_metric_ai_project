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
    "In Progress",
    "Review",
    "In Test",
)
CLOSED_STATUS_VULNERABILITY = ("Closed", "Resolved")
ISSUE_TYPES = ("Security Audit", "Vulnerability")
AUDIT_TYPES = ("Pre-release", "Regular", "Agile", "Permanent", "PCIDSS")
RESOLUTIONS = (
    "Fixed",
    "Answered",
    "Risk Accepted",
    "Duplicate",
    "Done",
    "Discarded",
    "Won't Do",
)
DATE_FORMAT_1 = "YYYY-MM-DD"
DATE_FORMAT_2 = "YYYY-MM-DD HH:MM:SS"
JOIN_KEY_SQL = "jira_audit_filtered.subtask_key = overall_vulnerability.ticket_key"


def _status_in_sql(statuses: tuple[str, ...]) -> str:
    values = ", ".join(f"'{status}'" for status in statuses)
    return f"status IN ({values})"


OPEN_STATUS_SQL = _status_in_sql(OPEN_STATUS_VULNERABILITY)
CLOSED_STATUS_SQL = _status_in_sql(CLOSED_STATUS_VULNERABILITY)
SECURITY_AUDIT_SQL = "ticket_key LIKE 'AUDIT-%'"
SECURITY_AUDIT_FOR_SUBSIDIARIES_SQL = "ticket_key LIKE 'EXTAUDIT-%'"
PENTEST_SQL = "ticket_key LIKE 'PENTEST-%'"
VULNERABILITY_VERIFICATION_SQL = "ticket_key LIKE 'VV-%'"
VULNERABILITY_REMEDIATION_SUPPORT_SQL = "ticket_key LIKE 'VRS-%'"
VULNERABILITY_TICKETS_SQL = "issue_type = 'Vulnerability'"
SECURITY_AUDIT_TICKETS_SQL = "issue_type = 'Security Audit'"


def build_sql_rules() -> tuple[str, ...]:
    return (
        f"When user asks about open/backlog tickets, use {OPEN_STATUS_SQL} on "
        "jira_audit_filtered.status.",
        f"When user asks about closed/resolved tickets, use {CLOSED_STATUS_SQL} on "
        "jira_audit_filtered.status.",
        f"For org/team/MTTR, JOIN overall_vulnerability with jira_audit_filtered ON "
        f"{JOIN_KEY_SQL}.",
        "For auditor KPIs, filter jira_audit_filtered.auditor (same person as "
        "overall_vulnerability.reporter). JOIN only when org/MTTR columns are needed.",
        "For status/priority/audit-type breakdowns, use jira_audit_filtered.",
        f"Use jira_audit_filtered as the main table. JOIN overall_vulnerability only when "
        f"org hierarchy, service_name, or MTTR columns are required ({JOIN_KEY_SQL}).",
        "Only SELECT statements. Never INSERT, UPDATE, DELETE, DROP, or ALTER.",
        f"jira_audit_filtered date columns use {DATE_FORMAT_1}. "
        f"overall_vulnerability datetime columns use {DATE_FORMAT_2}.",
        "There are columns with NULL values. Handle them appropriately in your queries.",
        "Use overall_vulnerability for organization hierarchy (l0–l5), service_name, and "
        f"MTTR. Always JOIN jira_audit_filtered ON {JOIN_KEY_SQL}.",
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
        ColumnDef(
            name="audit_type",
            type="TEXT",
            description="The type of audit (Pre-release, Regular, Agile, Permanent, PCIDSS).",
        ),
        ColumnDef(name="resolution", type="TEXT", description="How the ticket was resolved or closed."),
        ColumnDef(name="auditor", type="TEXT", description="The auditor who's responsible for the jira issue."),
        ColumnDef(name="assignee", type="TEXT", description="The one who assign the jira issue to the auditor."),
        ColumnDef(name="issue_type", type="TEXT", description="Usually we only have one issue type which is 'Vulnerability' because we focus on vulnerabilities."),
        ColumnDef(name="labels", type="TEXT", description="Any labels associated with the Jira issue."),
        ColumnDef(name="summary", type="TEXT", description="Title of the Jira issue."),
        ColumnDef(name="plan_end_date", type="TEXT", description=f"The planned end date for the audit task. Format: {DATE_FORMAT_1}."),
        ColumnDef(name="plan_start_date", type="TEXT", description=f"The planned start date for the audit task. Format: {DATE_FORMAT_1}."),
        ColumnDef(name="fix_deadline_date", type="TEXT", description=f"The deadline for fixing the vulnerability when the resolution is 'Risk Accepted'. Format: {DATE_FORMAT_1}."),
        ColumnDef(name="release_date", type="TEXT", description=f"The release date of the software release. Format: {DATE_FORMAT_1}."),
        ColumnDef(name="resolved_date", type="TEXT", description=f"The date when the Jira issue was risk accepted or closed. Format: {DATE_FORMAT_1}."),
        ColumnDef(name="updated_date", type="TEXT", description=f"The date when the Jira issue was last updated. Format: {DATE_FORMAT_1}."),
        ColumnDef(name="created_date", type="TEXT", description=f"The date when the Jira issue was created. Format: {DATE_FORMAT_1}.")
    )
)

OVERALL_VULNERABILITY = TableDef(
    name="overall_vulnerability",
    purpose="Vulnerability tickets with org hierarchy, resolution metrics, and MTTR.",
    use_when=(
        "Use for organization hierarchy (l0–l5), service_name, MTTR, and fix-deadline metrics. "
        f"JOIN jira_audit_filtered ON {JOIN_KEY_SQL} when filtering by auditor or audit_type."
    ),
    columns=(
        ColumnDef("ticket_key", "TEXT", "Vulnerability ticket key, this tickets has parent ticket."),
        ColumnDef("parent_key", "TEXT", "Parent ticket key, this is where the vulnerability ticket belongs."),
        ColumnDef("reporter", "TEXT", "The auditor responsible for the jira audit ticket."),
        ColumnDef("type", "TEXT", "Usually 'Vulnerability' (issue type, not audit type)."),
        ColumnDef("status", "TEXT", "Current JIRA issue status."),
        ColumnDef("priority", "TEXT", "Priority level (Blocker > Critical > Major > Minor > Trivial)."),
        ColumnDef("resolution", "TEXT", "How the ticket was resolved or closed."),
        ColumnDef("audit_type", "TEXT", "The type of audit associated with the ticket."),
        ColumnDef("created_date", "TEXT", f"Ticket created. Format: {DATE_FORMAT_2}."),
        ColumnDef("release_date", "TEXT", f"Planned release date. Format: {DATE_FORMAT_1}."),
        ColumnDef("plan_end_date", "TEXT", f"Planned end date. Format: {DATE_FORMAT_1}."),
        ColumnDef("resolution_date", "TEXT", f"When resolved. Empty if still open. Format: {DATE_FORMAT_1}."),
        ColumnDef("closed_date", "TEXT", f"When fully closed. Format: {DATE_FORMAT_1}."),
        ColumnDef("resolved_date", "TEXT", f"Alternate resolved timestamp. Format: {DATE_FORMAT_1}."),
        ColumnDef("fix_deadline", "TEXT", f"Target fix deadline. Format: {DATE_FORMAT_1}."),
        ColumnDef("isFixWithinDeadline", "TEXT", "Whether fix was within deadline."),
        ColumnDef("mttrToFixed", "REAL", "Mean time to resolve to fixed, in days."),
        ColumnDef("mttrToRiskAccepted", "REAL", "Mean time to resolve to risk accepted, in days."),
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


def format_column_mapping() -> str:
    return f"""## Column mapping (jira_audit_filtered | overall_vulnerability)
- subtask_key = ticket_key (JOIN key — use {JOIN_KEY_SQL}, not auditor = reporter)
- parent_key = parent_key
- auditor = reporter (same person; filter in WHERE, not JOIN ON)
- status = status
- audit_type = audit_type (not type; type is usually 'Vulnerability')
- resolution = resolution
- created_date = created_date (jira: {DATE_FORMAT_1}; vuln: {DATE_FORMAT_2})
- release_date = release_date
- plan_end_date = plan_end_date
- resolved_date = resolved_date
- fix_deadline_date = fix_deadline
Ticket prefix filters use overall_vulnerability.ticket_key or jira_audit_filtered.parent_key:
- {SECURITY_AUDIT_SQL} security audit
- {SECURITY_AUDIT_FOR_SUBSIDIARIES_SQL} subsidiary audit
- {PENTEST_SQL} pentest
- {VULNERABILITY_VERIFICATION_SQL} verification
- {VULNERABILITY_REMEDIATION_SUPPORT_SQL} remediation support"""


def format_query_patterns() -> str:
    return f"""## Query Patterns
When the user asks...                          | Use this approach
-----------------------------------------------|----------------------------------
Open/backlog count or by status/priority       | jira_audit_filtered WHERE {OPEN_STATUS_SQL} GROUP BY ...
Closed/resolved count                          | jira_audit_filtered WHERE {CLOSED_STATUS_SQL}
By organization/team/service                   | JOIN overall_vulnerability o ON {JOIN_KEY_SQL} GROUP BY o.org_name
Auditor performance (resolved/open by person)  | jira_audit_filtered WHERE auditor = '...' AND ...
MTTR / fix deadline metrics                    | overall_vulnerability JOIN jira_audit_filtered ON {JOIN_KEY_SQL}
This month / this year                         | jira: created_date LIKE 'YYYY-MM-%'; vuln: year/month columns
Open filter (use exactly): {OPEN_STATUS_SQL}
Closed filter (use exactly): {CLOSED_STATUS_SQL}
Join key (use exactly): {JOIN_KEY_SQL}"""


def build_schema_prompt() -> str:
    """Build the schema context string for the LLM system prompt."""
    sections = [
        "# Database Schema Context",
        "",
            "You analyze audit tickets data from a local SQLite database.",
            "The main table is jira_audit_filtered, which contains detailed information about Jira tickets related to audit tickets, including their status, priority, audit type, resolution, reporter, assignee, issue type, labels, summary, and various date fields. But if you need to answer user question about organization details of the audit tickets, such as which department is responsible for the ticket, which team is responsible for the ticket, etc., you can use overall_vulnerability table and always join with jira_audit_filtered to get the ticket details.",
        "",
        "## SQL Rules",
        *[f"- {rule}" for rule in build_sql_rules()],
        "",
        "## Business Definitions",
        format_enum("Open ticket statuses", OPEN_STATUS_VULNERABILITY),
        format_enum("Closed ticket statuses", CLOSED_STATUS_VULNERABILITY),
        format_enum("Issue ticket types", ISSUE_TYPES),
        format_enum("Audit types", AUDIT_TYPES),
        format_enum("Resolutions of audit tickets", RESOLUTIONS),
        f"When user says open/backlog, use: {OPEN_STATUS_SQL}",
        f"When user says closed/done, use: {CLOSED_STATUS_SQL}",
        f"For org details, JOIN overall_vulnerability ON {JOIN_KEY_SQL}.",
        "",
        format_column_mapping(),
        "",
        format_query_patterns(),
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