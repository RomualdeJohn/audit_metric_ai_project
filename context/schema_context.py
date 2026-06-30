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
AUDIT_TYPES = ("Pre-release", "Regular", "Agile", "Permanent", "PCIDSS")
RESOLUTIONS = (
    "Fixed",
    "Customer Timeout",
    "Risk Accepted",
    "Answered",
    "Duplicate",
    "Discarded",
    "Won't Fix",
    "Unresolved",
    "Implemented Request",
    "Invalid",
    "Done",
    "Working as Intended",
    "Cannot Reproduce",
    "Unsupported Environment",
    "Later",
    "Declined",
    "Approved",
    "Not a bug",
    "Known issue",
    "Rejected",
)
FIX_WITHIN_DEADLINE_VALUES = ("True", "False", "Not Still Closed/Resolved")
DATE_FORMAT_1 = "YYYY-MM-DD"
DATE_FORMAT_2 = "YYYY-MM-DD HH:MM:SS"

DATA_PROFILE = (
    "~34,000 vulnerability subtasks spanning 2017–2026",
    "~9% open/backlog, ~89% closed or resolved",
    "Dominant audit types: Pre-release (~62%), Regular (~36%)",
    "Parent tickets: ~85% AUDIT-*, ~13% EXTAUDIT-*, ~2% PENTEST-*",
    "Dominant priorities: Minor (~47%), Major (~34%), Critical (~13%)",
)

PRIORITY_ORDER_SQL = """CASE priority
  WHEN 'Blocker' THEN 1
  WHEN 'Critical' THEN 2
  WHEN 'Major' THEN 3
  WHEN 'Minor' THEN 4
  WHEN 'Trivial' THEN 5
  ELSE 6
END"""


def _status_in_sql(statuses: tuple[str, ...]) -> str:
    values = ", ".join(f"'{status}'" for status in statuses)
    return f"status IN ({values})"


OPEN_STATUS_SQL = _status_in_sql(OPEN_STATUS_VULNERABILITY)
CLOSED_STATUS_SQL = _status_in_sql(CLOSED_STATUS_VULNERABILITY)
SECURITY_AUDIT_SQL = "parent_key LIKE 'AUDIT-%'"
SECURITY_AUDIT_FOR_SUBSIDIARIES_SQL = "parent_key LIKE 'EXTAUDIT-%'"
PENTEST_SQL = "parent_key LIKE 'PENTEST-%'"
VULNERABILITY_VERIFICATION_SQL = "ticket_key LIKE 'VV-%'"
VULNERABILITY_REMEDIATION_SUPPORT_SQL = "ticket_key LIKE 'VRS-%'"


def build_sql_rules() -> tuple[str, ...]:
    return (
        "Use overall_vulnerability as the only allowed table.",
        f"When user asks about open/backlog tickets, use {OPEN_STATUS_SQL}.",
        f"When user asks about closed/resolved tickets, use {CLOSED_STATUS_SQL}.",
        "All rows are vulnerability subtasks (type = 'Vulnerability'). Scope by parent_key "
        "prefix for security audit, pentest, or subsidiary programs.",
        "For BU-level org breakdowns use l0_org_name; for team-level use org_name; "
        "l1_5_org_name for mid-level. Avoid l5_org_name unless user needs deepest level "
        "(sparse data).",
        "For auditor KPIs filter reporter; use reporter LIKE '%name%' because names are "
        "formatted as 'Last, First | Nick | ORG'.",
        "MTTR to Fixed: resolution = 'Fixed' AND mttrToFixed IS NOT NULL.",
        "MTTR to Risk Accepted: resolution = 'Risk Accepted' AND "
        "CAST(mttrToRiskAccepted AS REAL) — column is populated on all rows but only "
        "meaningful when resolution is Risk Accepted.",
        "Risk Accepted tickets usually have status = 'Resolved'. Fixed and Customer Timeout "
        "usually have status = 'Closed'. Do not infer resolution from status alone.",
        "For resolved timing prefer resolution_date; closed_date is often empty on Resolved "
        "tickets; use is_fixed_date when resolution = 'Fixed'.",
        "Avoid status_history unless user asks for status transitions (JSON-like text).",
        f"Order by severity with {PRIORITY_ORDER_SQL}.",
        "Only SELECT statements. Never INSERT, UPDATE, DELETE, DROP, or ALTER.",
        "There are columns with NULL values. Handle them appropriately in your queries.",
        "Use year, month, quarter_of_year, and week_of_year for time filters when helpful.",
        "Always include LIMIT 500 on queries that return rows.",
    )

TableName = Literal["overall_vulnerability"]

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


OVERALL_VULNERABILITY = TableDef(
    name="overall_vulnerability",
    purpose="Vulnerability subtasks with org hierarchy, resolution metrics, and MTTR.",
    use_when=(
        "Use for all queries: ticket counts, status/priority breakdowns, auditor KPIs, "
        "organization hierarchy (l0–l5, l1_5), service_name, MTTR, and fix-deadline metrics."
    ),
    columns=(
        ColumnDef("ticket_key", "TEXT", "Vulnerability subtask key."),
        ColumnDef("parent_key", "TEXT", "Parent audit ticket key."),
        ColumnDef(
            "reporter",
            "TEXT",
            "Auditor; format 'Last, First | Nick | ORG'. Use LIKE for name search.",
        ),
        ColumnDef("type", "TEXT", "Always 'Vulnerability' in this dataset."),
        ColumnDef("priority", "TEXT", "Blocker > Critical > Major > Minor > Trivial."),
        ColumnDef("resolution", "TEXT", "How the ticket was resolved; empty when open."),
        ColumnDef("status", "TEXT", "Current JIRA issue status."),
        ColumnDef(
            "status_history",
            "TEXT",
            "JSON-like status transitions; avoid unless user asks for history.",
        ),
        ColumnDef("audit_type", "TEXT", "Audit category (Pre-release, Regular, etc.)."),
        ColumnDef("created_date", "TEXT", f"Ticket opened. Format: {DATE_FORMAT_2}."),
        ColumnDef("release_date", "TEXT", f"Planned release date. Format: {DATE_FORMAT_1}."),
        ColumnDef("plan_end_date", "TEXT", f"Planned end date. Format: {DATE_FORMAT_1}."),
        ColumnDef(
            "resolution_date",
            "TEXT",
            f"When resolved; empty if open. Prefer for resolved-timing questions. Format: {DATE_FORMAT_1}.",
        ),
        ColumnDef(
            "closed_date",
            "TEXT",
            f"When fully closed; often empty on Resolved tickets. Format: {DATE_FORMAT_1}.",
        ),
        ColumnDef("resolved_date", "TEXT", f"Alternate resolved timestamp. Format: {DATE_FORMAT_1}."),
        ColumnDef(
            "is_fixed_date",
            "TEXT",
            f"When fix was applied (resolution = Fixed). Format: {DATE_FORMAT_1}.",
        ),
        ColumnDef(
            "fix_deadline",
            "TEXT",
            f"Target fix deadline (common on closed tickets). Format: {DATE_FORMAT_1}.",
        ),
        ColumnDef(
            "isFixWithinDeadline",
            "TEXT",
            f"Deadline compliance: {', '.join(FIX_WITHIN_DEADLINE_VALUES)}, or NULL.",
        ),
        ColumnDef(
            "mttrToFixed",
            "REAL",
            "Days to Fixed; use only when resolution = 'Fixed' and value IS NOT NULL.",
        ),
        ColumnDef(
            "mttrToRiskAccepted",
            "TEXT",
            "Days to risk acceptance; filter resolution = 'Risk Accepted', then CAST AS REAL.",
        ),
        ColumnDef("year", "INTEGER", "Year from created_date."),
        ColumnDef("week_of_year", "INTEGER", "Week 1–52."),
        ColumnDef("quarter_of_year", "INTEGER", "Quarter 1–4."),
        ColumnDef("month", "TEXT", "Month name (January, February, ...)."),
        ColumnDef("org_id", "TEXT", "Owning organization ID."),
        ColumnDef("org_name", "TEXT", "Team-level owning org (~78% populated)."),
        ColumnDef("service_id", "TEXT", "Service ID."),
        ColumnDef("service_name", "TEXT", "Service or application name."),
        ColumnDef(
            "components",
            "TEXT",
            "Usually duplicates org_id; prefer org_name for human-readable grouping.",
        ),
        ColumnDef("project_id", "TEXT", "Jira project ID."),
        ColumnDef("l0_org_id", "TEXT", "Top-level org ID."),
        ColumnDef("l0_org_name", "TEXT", "Business unit / company level (e.g. Executives)."),
        ColumnDef("l1_org_id", "TEXT", "Org hierarchy level 1 ID."),
        ColumnDef("l1_org_name", "TEXT", "Org hierarchy level 1."),
        ColumnDef("l1_5_org_id", "TEXT", "Org hierarchy level 1.5 ID."),
        ColumnDef("l1_5_org_name", "TEXT", "Mid-level org (~72% populated)."),
        ColumnDef("l2_org_id", "TEXT", "Org hierarchy level 2 ID."),
        ColumnDef("l2_org_name", "TEXT", "Org hierarchy level 2."),
        ColumnDef("l3_org_id", "TEXT", "Org hierarchy level 3 ID."),
        ColumnDef("l3_org_name", "TEXT", "Org hierarchy level 3."),
        ColumnDef("l4_org_id", "TEXT", "Org hierarchy level 4 ID."),
        ColumnDef("l4_org_name", "TEXT", "Org hierarchy level 4."),
        ColumnDef("l5_org_id", "TEXT", "Org hierarchy level 5 ID."),
        ColumnDef(
            "l5_org_name",
            "TEXT",
            "Deepest org level; sparse (~1%). Avoid unless user requests it.",
        ),
    ),
)

TABLE_DEFINITIONS: tuple[tuple[str, TableDef], ...] = (
    ("overall_vulnerability", OVERALL_VULNERABILITY),
)


def format_enum(title: str, values: tuple[str, ...]) -> str:
    return f"{title}: {', '.join(values)}"


def format_data_profile() -> str:
    return "## Dataset snapshot\n" + "\n".join(f"- {line}" for line in DATA_PROFILE)


def format_status_resolution_notes() -> str:
    return """## Status vs resolution
- Open/backlog tickets have empty resolution
- Risk Accepted → usually status = 'Resolved' (not Closed)
- Fixed, Customer Timeout, Answered → usually status = 'Closed'
- Customer Timeout is the 2nd most common resolution (~19% of all tickets)
- Filter on resolution for outcome questions; use status for backlog vs done"""


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


def format_column_notes() -> str:
    return f"""## Column notes
- type is always 'Vulnerability'; audit_type is the audit program category
- ticket_key is the vulnerability subtask; parent_key is the parent audit ticket
- audit_type may be NULL on ~116 rows; use IS NOT NULL when grouping by audit_type
- components usually equals org_id; use org_name for readable team names

## Organization hierarchy
- l0_org_name: business unit level (largest share: Executives)
- org_name: team-level owning org
- l1_5_org_name: mid-level hierarchy
- l5_org_name: sparse; only use when user asks for deepest granularity

## Date fields (which to use)
- created_date: when opened ({DATE_FORMAT_2})
- resolution_date: when resolved (prefer for resolved-this-period questions)
- closed_date: when fully closed (often empty on status = Resolved)
- is_fixed_date: when marked Fixed
- fix_deadline: target fix deadline on most closed tickets
- release_date / plan_end_date: planning dates

## MTTR
- AVG(mttrToFixed) WHERE resolution = 'Fixed' AND mttrToFixed IS NOT NULL
- AVG(CAST(mttrToRiskAccepted AS REAL)) WHERE resolution = 'Risk Accepted'
- Do not average mttrToRiskAccepted without filtering resolution

## Deadline compliance
- isFixWithinDeadline values: {', '.join(FIX_WITHIN_DEADLINE_VALUES)}

## Audit program scope (parent_key)
- {SECURITY_AUDIT_SQL} — security audit (~85% of rows)
- {SECURITY_AUDIT_FOR_SUBSIDIARIES_SQL} — subsidiary audit (~13%)
- {PENTEST_SQL} — pentest (~2%)

## Vulnerability subtask scope (ticket_key; rare in current data)
- {VULNERABILITY_VERIFICATION_SQL} — verification (~106 rows)
- {VULNERABILITY_REMEDIATION_SUPPORT_SQL} — remediation support (may be empty)"""


def format_query_patterns() -> str:
    return f"""## Query Patterns
When the user asks...                          | Use this approach
-----------------------------------------------|----------------------------------
Open/backlog count or by status/priority       | WHERE {OPEN_STATUS_SQL} GROUP BY status or priority
Closed/resolved count                          | WHERE {CLOSED_STATUS_SQL}
By business unit                               | GROUP BY l0_org_name
By team / org                                  | GROUP BY org_name
By service                                     | GROUP BY service_name
Auditor performance                            | WHERE reporter LIKE '%name%' AND status/resolution filters
Average MTTR to Fixed                          | AVG(mttrToFixed) WHERE resolution='Fixed' AND mttrToFixed IS NOT NULL
Average MTTR to Risk Accepted                  | AVG(CAST(mttrToRiskAccepted AS REAL)) WHERE resolution='Risk Accepted'
Customer Timeout count                         | WHERE resolution = 'Customer Timeout'
Resolved this month/year                       | resolution_date LIKE 'YYYY-MM-%' or year/month columns
Priority ranking                               | ORDER BY {PRIORITY_ORDER_SQL}
Open filter (use exactly): {OPEN_STATUS_SQL}
Closed filter (use exactly): {CLOSED_STATUS_SQL}"""


def build_schema_prompt() -> str:
    """Build the schema context string for the LLM system prompt."""
    sections = [
        "# Database Schema Context",
        "",
        "You analyze vulnerability ticket data from a local SQLite database.",
        "The only table is overall_vulnerability — vulnerability subtasks linked to "
        "parent audit tickets via parent_key.",
        "",
        format_data_profile(),
        "",
        "## SQL Rules",
        *[f"- {rule}" for rule in build_sql_rules()],
        "",
        "## Business Definitions",
        format_enum("Open ticket statuses", OPEN_STATUS_VULNERABILITY),
        format_enum("Closed ticket statuses", CLOSED_STATUS_VULNERABILITY),
        format_enum("Audit types", AUDIT_TYPES),
        format_enum("Resolutions", RESOLUTIONS),
        format_enum("Fix-within-deadline values", FIX_WITHIN_DEADLINE_VALUES),
        "",
        format_status_resolution_notes(),
        "",
        format_column_notes(),
        "",
        format_query_patterns(),
        "",
        "## Tables",
        "",
        format_table(OVERALL_VULNERABILITY),
    ]

    return "\n".join(sections)

SCHEMA_CONTEXT = build_schema_prompt()

if __name__ == "__main__":
    print(SCHEMA_CONTEXT)
