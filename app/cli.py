"""CLI (SPEC §7 P0-5): 一条命令串起预测→报价→出清→结算→回测, 跑出 BacktestReport.

用法:
  python -m app.cli backtest [--days N] [--line-limit MW] [--model persistence|xgboost|lstm]
  python -m app.cli serve            # 起后端 (uvicorn)
依赖 click. 主线全链路复现 (SPEC §1).
"""

from __future__ import annotations

import json

import click
import numpy as np

from app.core.config import settings
from app.domain.settlement import CfdContract
from app.domain.units import default_network, default_units
from app.services.backtest import run_backtest
from app.services.clearing import ClearingRequestDTO
from scripts.seed_demo import seed_market, to_clearing_input


@click.group()
def cli() -> None:
    """spark-pricing 命令行."""


@cli.command("backtest")
@click.option("--days", default=2, show_default=True, help="合成历史天数 (1天=96 时段)")
@click.option(
    "--line-limit", "line_limit", default=None, type=float, help="线路潮流上限 MW (默认 settings)"
)
@click.option(
    "--model",
    "model",
    default=None,
    type=click.Choice(["persistence", "xgboost", "lstm"]),
    help="预测模型",
)
def backtest_cmd(days: int, line_limit: float | None, model: str | None) -> None:
    """跑回测主线: 出清 + 结算 + 指标, 输出 BacktestReport (JSON 到 stdout)."""
    fmax = line_limit if line_limit is not None else settings.line_flow_limit_mw
    m = seed_market(days=days, line_flow_limit_mw=fmax)
    ci = to_clearing_input(m, periods=days * 96)
    units = default_units()
    net = default_network(fmax)
    req = ClearingRequestDTO(
        units=units,
        network=net,
        load_per_node=ci.load_per_node,
        reserve_requirement_mw=ci.reserve_requirement_mw,
        periods=days * 96,
    )
    # 一个差价合约 (中长期层): 合约价 300, 量 1000, 参考价取合成历史均值.
    cfd = CfdContract(
        strike_price=300.0,
        quantity=1000.0,
        reference_px=float(np.mean(m.lmp_load_history)),
    )
    rep = run_backtest(
        clearing_req=req,
        history_lmp=m.lmp_load_history,
        load_node="LOAD",
        forecast_model=model,
        cfd=cfd,
    )
    click.echo(json.dumps(rep.model_dump(mode="json"), ensure_ascii=False, indent=2))


@cli.command("serve")
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=8000, show_default=True)
def serve_cmd(host: str, port: int) -> None:
    """起 FastAPI 后端 (uvicorn) — P1 路由挂载后 /docs 可用."""
    import uvicorn

    uvicorn.run("app.main:app", host=host, port=port, reload=settings.debug)


def main() -> None:
    cli(standalone_mode=True)


if __name__ == "__main__":
    main()
