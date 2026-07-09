# ADR 0002 · 预测器接口: Persistence 默认 + XGBoost 可选 + LSTM stub

## 状态
Accepted

## 背景
demo 要演示价格预测并支撑回测策略2 (边际成本 + 预测加成), 且接口即主要交付物之一.
但 1h 内 LSTM 真训练装不上 (重依赖/需大量数据/需 GPU), 强行上会拖垮交付.

## 决策
定义统一 Forecaster ABC: `forecast(history: np.ndarray, horizon) -> np.ndarray` + `name`.
- **Persistence** (零依赖) 默认, 实跑: 近一个日周期同相位 + 漂移修正.
- **XGBoost** 可选依赖: 装则真跑 (滞后特征 + 日内相位回归), 不装则工厂回退 Persistence 且 log warn.
- **LSTM** stub: `__init__` log warn "stub: returns persistence", forecast 返回 Persistence 结果.
工厂按 `settings.DEFAULT_FORECASTER` 或请求参数选, 缺则优雅回退.
**绝不把 LSTM 标成真结果**; 回测与指标仅基于 Persistence/XGBoost 真出数.

## 理由
- 诚实 > 性能假象: 把 LSTM 写成"真跑"再展示漂亮的回测, 一旦被追问训练管线即露馅;
  stub 明示 + Persistence 真跑, 反而展示工程取舍判断力.
- 接口在场: 真平台接入 LSTM/XGBoost 只需实现同一 ABC, 不改调用方.
- XGBoost 作为"可选安装包"使回测能显示真 ML 对 Persistence 的小幅胜出 (哪怕微小), 证"真 ML".

## 后果
- 正面: 接口清晰、依赖可控、1h 可交付; 接入新模型零改动声称面.
- 负面/边界: LSTM 不真展示, 须在 backtest summary 与 README 诚实声明.

## 相关
SPEC §3.4, §3.5 诚实验证. PRD §4 "LSTM 真训练" 列为 out-of-scope.