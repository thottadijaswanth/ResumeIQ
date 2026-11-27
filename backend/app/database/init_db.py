import logging
from sqlalchemy import inspect, text
from backend.app.database.session import Base, engine
from backend.app.models import (
    Analysis,
    Application,
    Job,
    JobEmbedding,
    Resume,
    ResumeEmbedding,
    ScreeningRun,
    User,
)

logger = logging.getLogger(__name__)

# Incremental additive column definitions for seamless upgrades of existing SQLite/Postgres DBs
_COLUMN_MIGRATIONS = {
    "jobs": [
        ("work_mode", "VARCHAR(32) NOT NULL DEFAULT 'Hybrid'"),
        ("min_experience", "FLOAT"),
        ("max_experience", "FLOAT"),
        ("required_skills", "JSON"),
        ("preferred_skills", "JSON"),
        ("education_requirements", "JSON"),
        ("employment_type", "VARCHAR(64)"),
        ("notice_period", "VARCHAR(64)"),
        ("location_required", "BOOLEAN NOT NULL DEFAULT 0"),
    ],
    "resumes": [
        ("file_hash", "VARCHAR(64)"),
        ("candidate_years", "FLOAT"),
        ("candidate_location", "VARCHAR(255)"),
        ("combined_embedding", "JSON"),
        ("processing_status", "VARCHAR(32) NOT NULL DEFAULT 'ready'"),
        ("processing_error", "TEXT"),
        ("ai_provider_used", "VARCHAR(32)"),
        ("ai_model_used", "VARCHAR(128)"),
        ("processed_at", "DATETIME"),
    ],
    "analyses": [
        ("screening_run_id", "VARCHAR(36)"),
        ("match_classification", "VARCHAR(32)"),
        ("ai_reranked", "BOOLEAN NOT NULL DEFAULT 0"),
        ("hard_filter_passed", "BOOLEAN NOT NULL DEFAULT 1"),
        ("hard_filter_notes", "JSON"),
        ("rank_position", "INTEGER"),
    ],
}


def _apply_additive_column_migrations() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table_name, columns in _COLUMN_MIGRATIONS.items():
            if table_name not in existing_tables:
                continue
            existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
            for col_name, col_ddl in columns:
                if col_name not in existing_cols:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_ddl}"))
                    logger.info(f"Added column '{col_name}' to table '{table_name}'.")


def init_db() -> None:
    """Create all tables in the database and apply additive column migrations."""
    try:
        logger.info("Initializing database tables...")
        Base.metadata.create_all(bind=engine)
        _apply_additive_column_migrations()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise e


if __name__ == "__main__":
    init_db()
