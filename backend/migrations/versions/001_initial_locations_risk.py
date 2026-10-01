"""create locations and risk_scores tables

Revision ID: 001_initial_locations_risk
Revises: 
Create Date: 2026-10-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = '001_initial_locations_risk'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create locations table
    op.create_table(
        'locations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lon', sa.Float(), nullable=False),
        sa.Column('geometry', Geometry(geometry_type='POINT', srid=4326, spatial_index=False), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_locations_id'), 'locations', ['id'], unique=False)

    # Create risk_scores table
    op.create_table(
        'risk_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=False),
        sa.Column('risk_score', sa.Float(), nullable=False),
        sa.Column('risk_level', sa.String(length=20), nullable=False),
        sa.Column('chlorophyll_a', sa.Float(), nullable=True),
        sa.Column('sst_anomaly', sa.Float(), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_risk_scores_id'), 'risk_scores', ['id'], unique=False)
    op.create_index(op.f('ix_risk_scores_location_id'), 'risk_scores', ['location_id'], unique=False)
    op.create_index(op.f('ix_risk_scores_detected_at'), 'risk_scores', ['detected_at'], unique=False)
    op.create_index('idx_risk_scores_loc_detected', 'risk_scores', ['location_id', 'detected_at'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_risk_scores_loc_detected', table_name='risk_scores')
    op.drop_index(op.f('ix_risk_scores_detected_at'), table_name='risk_scores')
    op.drop_index(op.f('ix_risk_scores_location_id'), table_name='risk_scores')
    op.drop_index(op.f('ix_risk_scores_id'), table_name='risk_scores')
    op.drop_table('risk_scores')
    op.drop_index(op.f('ix_locations_id'), table_name='locations')
    op.drop_table('locations')
