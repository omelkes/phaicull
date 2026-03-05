"""SQLite schema documentation and constants for Phaicull.

Two databases (per AGENTS.md and TODO):
- Project DB: one per photo directory at {project}/phaicull/phaicull.db.
  Tables: schema_version, files, metrics, groups.
- Registry DB: one in install dir at .projects/registry.db.
  Tables: schema_version, projects.
WAL mode is enabled on every connection (see migrate.py and dao.py).
"""

from __future__ import annotations

# Project DB: relative path to DB file inside a project directory
PROJECT_DB_NAME = "phaicull.db"
PROJECT_PHAICULL_SUBDIR = "phaicull"

# Registry DB: path segment under install/base directory
PROJECTS_DIR_NAME = ".projects"
REGISTRY_DB_NAME = "registry.db"

# Project DB tables (002_project_schema)
TABLE_FILES = "files"
TABLE_METRICS = "metrics"
TABLE_GROUPS = "groups"
TABLE_SCHEMA_VERSION = "schema_version"

# Registry DB table
TABLE_PROJECTS = "projects"

# Column names (stable API — see AGENTS.md Interface Stability)
# files
COL_FILE_ID = "id"
COL_FILE_PATH = "file_path"
COL_CONTENT_HASH = "content_hash"
COL_STATUS = "status"
COL_GROUP_ID = "group_id"
COL_CREATED_AT = "created_at"
COL_UPDATED_AT = "updated_at"

# metrics
COL_METRIC_ID = "id"
COL_FILE_ID_FK = "file_id"
COL_METRIC_NAME = "metric_name"
COL_VALUE_REAL = "value_real"
COL_VALUE_TEXT = "value_text"

# groups
COL_GROUP_ID_PK = "id"
COL_GROUP_CREATED_AT = "created_at"

# projects (registry)
COL_PROJECT_ID = "id"
COL_PROJECT_PATH = "path"
COL_PROJECT_NAME = "name"
COL_PROJECT_ADDED_AT = "added_at"
