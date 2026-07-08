"""日前出清引擎 (SPEC §3.2) — demo 的硬核可信度所在.

模型: 能量 + 1 个旋转备用, 联合出清的 LP (固定机组组合, 即 SCED 经济调度层).
决策变量:
  P[g,t]  机组 g 在时段 t 的出力 (MW)
  R[g,t]  机组 g 在时段 t 提供的旋转备用 (MW)
目标: min Σ C_g(P[g,t])  (用边际成本近似的分段线性化足够; 为 LP 用成本曲线两点线性化)
约束:
  - 节点功率平衡 (每节点每时段): Σ_gen P == node load      <- 对偶变量即节点 LMP
  - 备用平衡 (每时段):           Σ R[g,t] >= ReserveReq[t]
  - 机组出力上下限:               P_min <= P <= P_max ; P + R <= P_max
  - 爬坡:                         |P[g,t] - P[g,t-1]| <= ramp
  - 线路潮流 (2 节点 DC):          F = (REF 节点净注入), |F| <= line_flow_limit  -> 制造阻塞
LMP 取法: 读**节点功率平衡约束的对偶变量**当节点 LMP.
  - 参考节点 LMP = REF 平衡对偶
  - 负荷节点 LMP = LOAD 平衡对偶
  - 阻塞价 = 负荷节点 LMP - 参考节点 LMP  (负荷节点 LMP 通常更高, 因便宜基荷被线路卡住)
  - 损耗价 = 0 (注释: 生产才计; SPEC §3.2)
备用模型简化: 备用对总成本无直接贡献 (只在约束里出现), 取备用平衡的对偶作"备用价格"信息项.

为何不做 UC 整数: SCUC(开停机整数)需 MILP, 1h 内不稳且对 LMP 真实性无增益; 固定组合下
LMP 仍真实有效 (ADR 0001 详述).
"""

from __future__ import annotations

from dataclasses import dataclass

import pulp

from app.core.errors import ClearingInfeasibleError
from app.domain.units import Network, Unit


@dataclass(frozen=True)
class ClearingInput:
    """单次出清输入 (单时段或多时段)."""

    units: list[Unit]
    network: Network
    load_per_node: dict[str, list[float]]  # node_id -> [load per period] MW
    reserve_requirement_mw: list[float]  # [reserve per period] MW (统一备用需求)
    periods: int  # 时段数


@dataclass(frozen=True)
class PeriodResult:
    period: int
    p: dict[str, float]  # unit_id -> 出力 (MW)
    r: dict[str, float]  # unit_id -> 旋转备用 (MW)
    lmp: dict[str, float]  # node_id -> LMP (元/MWh)
    lmp_components: dict[str, dict[str, float]]  # node_id -> {energy, congestion, loss}
    line_flow_mw: float  # 该时段线路潮流 (REF -> LOAD 为正)
    blocked: bool  # 线路是否满载(绝对值达限)


@dataclass(frozen=True)
class ClearingResult:
    periods: list[PeriodResult]
    status: str  # "optimal"
    total_cost: float  # 元 (Σ cost)


def _dual(prob: pulp.LpProblem, name: str) -> float:
    """安全取 CBC 对偶值 (求解未生成对偶时返回 0.0)."""
    con = prob.constraints.get(name)
    if con is None or con.pi is None:
        return 0.0
    return float(con.pi)


def solve_clearing(inp: ClearingInput) -> ClearingResult:
    """求解日前联合出清 (能量 + 旋转备用) 的 LP, 返回含节点 LMP 的结果.

    节点平衡约束的对偶变量即为该节点 LMP (影子价). 当线路满载(阻塞)时, 两节点 LMP
    会产生差值 -> 阻塞价 > 0; 无阻塞时两者相等, 阻塞价 = 0.
    """
    units = inp.units
    nodes = inp.network.nodes
    ref = inp.network.reference_node
    load = inp.network.load_node
    f_max = inp.network.line_flow_limit_mw
    T = inp.periods

    prob = pulp.LpProblem("day_ahead_clearing", pulp.LpMinimize)

    # ---- 决策变量 ----
    P: dict[tuple[str, int], pulp.LpVariable] = {}
    R: dict[tuple[str, int], pulp.LpVariable] = {}
    for g in units:
        for t in range(T):
            P[(g.unit_id, t)] = pulp.LpVariable(
                f"P_{g.unit_id}_{t}", lowBound=g.p_min, upBound=g.p_max, cat="Continuous"
            )
            R[(g.unit_id, t)] = pulp.LpVariable(
                f"R_{g.unit_id}_{t}", lowBound=0.0, upBound=g.p_max, cat="Continuous"
            )

    # ---- 目标: min Σ C_g(P) -- 二次成本用两点线性化近似 (LP). ----
    # C(P)=aP^2+bP+c 在 [P_min,P_max] 用 N 点割线近似单调增 (凸二次): 取几个采样点, 加
    # SOS-free 的分段线性. 简化: 用边际成本在 (P_min+P_max)/2 处的常数线性化,
    # 即 cost ≈ mc*p + (cost(mid)-mc*mid), 保证 LP 单调且对偶经济意义清晰.
    cost_terms = []
    for g in units:
        for t in range(T):
            mid = 0.5 * (g.p_min + g.p_max)
            mc = g.marginal_cost(mid)  # 元/MWh
            intercept = g.cost(mid) - mc * mid
            cost_terms.append(mc * P[(g.unit_id, t)] + intercept)
    prob += pulp.lpSum(cost_terms)

    # ---- 线路潮流 (2 节点 DC): F = REF -> LOAD 为正方向. ----
    # F 作为传输项同时进入两个节点平衡方程:
    #   REF 平衡:  Σ_REF P - F == REF_load   (本地发一部分供本地, 余量外送)
    #   LOAD 平衡: Σ_LOAD P + F == LOAD_load  (本地发 + 受入 == 本地负荷)
    # F 单独约束 |F| <= f_max (线路容量), 制造阻塞. 两者相加即 Σ_all P == Σ_all load.
    F: dict[int, pulp.LpVariable] = {}
    for t in range(T):
        F[t] = pulp.LpVariable(f"F_{t}", lowBound=-f_max, upBound=f_max, cat="Continuous")

    # ---- 节点功率平衡 (对偶 = 节点 LMP). 引入潮流 F 作传输项. ----
    # prob.addConstraint 返回 None, 但 CBC 的对偶存于 prob.constraints[name].pi;
    # 故此处只记约束名, 求解后按名取对偶.
    balance_name: dict[tuple[str, int], str] = {}
    for t in range(T):
        ref_gen = pulp.lpSum(P[(g.unit_id, t)] for g in units if g.node_id == ref)
        load_gen = pulp.lpSum(P[(g.unit_id, t)] for g in units if g.node_id == load)
        bname_ref = f"bal_{ref}_{t}"
        bname_load = f"bal_{load}_{t}"
        prob.addConstraint(ref_gen - F[t] == inp.load_per_node[ref][t], name=bname_ref)
        prob.addConstraint(load_gen + F[t] == inp.load_per_node[load][t], name=bname_load)
        balance_name[(ref, t)] = bname_ref
        balance_name[(load, t)] = bname_load

    # ---- 备用平衡 (对偶 = 备用价格, 信息项) ----
    for t in range(T):
        prob.addConstraint(
            pulp.lpSum(R[(g.unit_id, t)] for g in units) >= inp.reserve_requirement_mw[t],
            name=f"reserve_{t}",
        )

    # ---- 机组: P + R <= P_max (备用容量不超额) ----
    for g in units:
        for t in range(T):
            prob.addConstraint(
                P[(g.unit_id, t)] + R[(g.unit_id, t)] <= g.p_max, name=f"cap_{g.unit_id}_{t}"
            )

    # ---- 爬坡 ----
    for g in units:
        for t in range(1, T):
            prob.addConstraint(
                P[(g.unit_id, t)] - P[(g.unit_id, t - 1)] <= g.ramp_up, name=f"ru_{g.unit_id}_{t}"
            )
            prob.addConstraint(
                P[(g.unit_id, t - 1)] - P[(g.unit_id, t)] <= g.ramp_down, name=f"rd_{g.unit_id}_{t}"
            )

    # ---- 求解 ----
    solver = pulp.PULP_CBC_CMD(msg=False)
    status = prob.solve(solver)
    if pulp.LpStatus[status] != "Optimal":
        raise ClearingInfeasibleError(
            f"日前出清无可行解 (LP status={pulp.LpStatus[status]}); 检查负荷/备用/线路约束"
        )

    # ---- 提取结果 + 对偶 LMP ----
    period_results: list[PeriodResult] = []
    total_cost = 0.0
    for t in range(T):
        p_t = {g.unit_id: float(P[(g.unit_id, t)].varValue or 0.0) for g in units}
        r_t = {g.unit_id: float(R[(g.unit_id, t)].varValue or 0.0) for g in units}
        # 对偶: CBC 存于 prob.constraints[name].pi. 取节点平衡对偶作 LMP.
        lmp: dict[str, float] = {}
        comps: dict[str, dict[str, float]] = {}
        ref_lmp = _dual(prob, balance_name[(ref, t)])
        load_lmp = _dual(prob, balance_name[(load, t)])
        lmp[ref] = ref_lmp
        lmp[load] = load_lmp
        for node in nodes:
            base = ref_lmp
            # SIM: 阻塞价 = 该节点 LMP - 参考节点 LMP; 损耗 = 0 (注释生产才计).
            congestion = 0.0 if node == ref else load_lmp - ref_lmp
            comps[node] = {"energy": base, "congestion": congestion, "loss": 0.0}
        flow = float(F[t].varValue or 0.0)
        blocked = abs(flow) >= f_max - 1e-6
        period_results.append(
            PeriodResult(
                period=t,
                p=p_t,
                r=r_t,
                lmp=lmp,
                lmp_components=comps,
                line_flow_mw=flow,
                blocked=blocked,
            )
        )
        for g in units:
            total_cost += g.cost(p_t[g.unit_id])  # 真实成本累计 (报告用)
    return ClearingResult(periods=period_results, status="optimal", total_cost=total_cost)
