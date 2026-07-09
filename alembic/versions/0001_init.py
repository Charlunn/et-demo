"""baseline init: price_tick / bid / clearing_result / contract (+ ix_price_tick_node_ts).

Revision ID: 0001_init
Revises:
Create Date: 2024-01-01 00:00:00

SPEC §4.6: Alembic baseline; prod 不用 create_all. CI 跑 alembic upgrade head.
Postgres 1h 聚合用 date_trunc 等价 time_bucket (time_bucket 需 TimescaleDB 扩展,
注释标生产才上 create_hypertable; 原生 PG 用 date_trunc 即可).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import reflection  # noqa


revision: str = "0001_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "price_tick",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ts", sa.DateTime, nullable=False),
        sa.Column("node_id", sa.String(16), nullable=False),
        sa.Column("series_type", sa.String(16), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("quality_flag", sa.String(16), nullable=False, server_default="OK"),
        sa.Column("ingested_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_price_tick_ts", "price_tick", ["ts"])
    op.create_index("ix_price_tick_node_ts", "price_tick", ["node_id", "ts"])

    op.create_table(
        "bid",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("unit_id", sa.String(16), nullable=False),
        sa.Column("strategy", sa.String(32), nullable=False),
        sa.Column("risk_markup", sa.Float, nullable=False, server_default="0"),
        sa.Column("segment_count", sa.Integer, nullable=False),
        sa.Column("segments_json", sa.String, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_bid_unit_id", "bid", ["unit_id"])

    op.create_table(
        "clearing_result",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("periods", sa.Integer, nullable=False),
        sa.Column("line_flow_limit_mw", sa.Float, nullable=False),
        sa.Column("total_cost", sa.Float, nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="optimal"),
        sa.Column("payload_json", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "contract",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("contract_id", sa.String(32), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False, server_default="cfd"),
        sa.Column("strike_price", sa.Float, nullable=False),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("reference_px", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_contract_contract_id", "contract", ["contract_id"])

    # 1h 聚合 view (SQLite 用 strftime; Postgres 用 date_trunc 等价 time_bucket
    # — time_bucket 需 TimescaleDB 扩展, 此处用原生 date_trunc, 注释标生产才上 hypertable).
    bind = op.get_bind()
    url = str(bind.engine.url)
    if url.startswith("postgres"):
        op.execute(
            "CREATE OR REPLACE VIEW price_1h AS "
            "SELECT node_id, series_type, date_trunc('hour', ts) AS hour, "
            "avg(value) AS avg_value, count(*) AS n "
            "FROM price_tick GROUP BY node_id, series_type, date_trunc('hour', ts)"
        )
    else:
        op.execute(
            "CREATE VIEW IF NOT EXISTS price_1h AS "
            "SELECT node_id, series_type, "
            "strftime('%Y-%m-%d %H:00', ts) AS hour, avg(value) AS avg_value, count(*) AS n "
            "FROM price_tick GROUP BY node_id, series_type, strftime('%Y-%m-%d %H:00', ts)"
        )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS price_1h")
    op.drop_index("ix_contract_contract_id", table_name="contract")
    op.drop_table("contract")
    op.drop_table("clearing_result")
    op.drop_index("ix_bid_unit_id", table_name="bid")
    op.drop_table("bid")
    op.drop_index("ix_price_tick_node_ts", table_name="price_tick")
    op.drop_index("ix_price_tick_ts", table_name="price_tick")
    op.drop_table("price_tick")