"""
0002_add_screening_projects.py
------------------------------
Adds screening_projects table and project_id FK on screening_results.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision      = "0002"
down_revision = "0001"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        "screening_projects",
        sa.Column("id",          postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id",     postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title",       sa.String(255), nullable=False),
        sa.Column("description", sa.Text(),      nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_screening_projects_id",      "screening_projects", ["id"],      unique=False)
    op.create_index("ix_screening_projects_user_id", "screening_projects", ["user_id"], unique=False)

    # Add project_id to existing screening_results (nullable so old rows are unaffected)
    op.add_column(
        "screening_results",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_screening_results_project_id",
        "screening_results", "screening_projects",
        ["project_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_screening_results_project_id", "screening_results", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_screening_results_project_id", table_name="screening_results")
    op.drop_constraint("fk_screening_results_project_id", "screening_results", type_="foreignkey")
    op.drop_column("screening_results", "project_id")
    op.drop_index("ix_screening_projects_user_id", table_name="screening_projects")
    op.drop_index("ix_screening_projects_id",      table_name="screening_projects")
    op.drop_table("screening_projects")