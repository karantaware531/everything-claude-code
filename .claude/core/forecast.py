#!/usr/bin/env python3
"""
forecast.py \u2014 linear trend extrapolation over scoring history.

v5 temporal intelligence primitive. Given a metric and a horizon, fit a simple
linear trend over recent data and project forward N tasks. Honest scope: this
is NOT neural time-series. It's least-squares linear extrapolation, which is
the stdlib intermediate: useful for surfacing "trending down" signals that the
performance_optimizer can act on.

Supported metrics:
    success_rate        \u2014 pass fraction over sliding window
    avg_reward          \u2014 mean reward (goal_keeper-stamped entries)
    avg_duration_ms     \u2014 mean latency

Persisted to memory/forecasts.json.

Usage (CLI):
    python forecast.py --metric success_rate --horizon 10
    python forecast.py --metric avg_reward --horizon 5 --window 30

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/
HISTORY = ROOT / "memory" / "agent_history.json"
FORECASTS = ROOT / "memory" / "forecasts.json"

DEFAULT_WINDOW = 20
MIN_SAMPLES = 3

ALERT_THRESHOLDS = {
    "success_rate":    {"below": 0.5},
    "avg_reward":      {"below": 0.0},
    "avg_duration_ms": {"above": 60000},   # > 60s median = worry
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(default)


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    tmp.replace(path)


def _extract_series(entries: list[dict], metric: str, window: int) -> list[float]:
    recent = entries[-window:]
    series: list[float] = []
    for e in recent:
        if metric == "success_rate":
            series.append(1.0 if e.get("success") else 0.0)
        elif metric == "avg_reward":
            r = e.get("reward")
            if isinstance(r, (int, float)):
                series.append(float(r))
        elif metric == "avg_duration_ms":
            d = e.get("metrics", {}).get("duration_ms")
            if isinstance(d, (int, float)):
                series.append(float(d))
    return series


def _linear_fit(series: list[float]) -> tuple[float, float]:
    """Least-squares slope, intercept. y = slope * x + intercept (x is index)."""
    n = len(series)
    if n < 2:
        return 0.0, series[0] if series else 0.0
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(series) / n
    num = sum((xs[i] - mean_x) * (series[i] - mean_y) for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n))
    if den == 0:
        return 0.0, mean_y
    slope = num / den
    intercept = mean_y - slope * mean_x
    return slope, intercept


def _classify_trend(slope: float, metric: str) -> str:
    # For metrics where higher is better, positive slope is good.
    higher_is_better = metric in ("success_rate", "avg_reward")
    if abs(slope) < 1e-4:
        return "flat"
    if higher_is_better:
        return "improving" if slope > 0 else "declining"
    return "worsening" if slope > 0 else "improving"


def _confidence(n_samples: int) -> str:
    if n_samples < MIN_SAMPLES:
        return "insufficient"
    if n_samples < 10:
        return "low"
    if n_samples < 25:
        return "medium"
    return "high"


def forecast(metric: str, horizon_tasks: int = 10, window: int = DEFAULT_WINDOW) -> dict:
    history = _load(HISTORY, {"entries": []})
    entries = history.get("entries", []) or []
    series = _extract_series(entries, metric, window)

    if len(series) < MIN_SAMPLES:
        result = {
            "metric":     metric,
            "window":     window,
            "horizon":    horizon_tasks,
            "samples":    len(series),
            "current":    series[-1] if series else None,
            "trend":      "unknown",
            "projected":  None,
            "confidence": "insufficient",
            "note":       f"need at least {MIN_SAMPLES} samples",
            "built_at":   _now_iso(),
        }
        return result

    current = series[-1]
    slope, intercept = _linear_fit(series)
    projected_index = len(series) - 1 + horizon_tasks
    projected = slope * projected_index + intercept
    # Clip success_rate and reward to plausible bounds.
    if metric == "success_rate":
        projected = max(0.0, min(1.0, projected))
    elif metric == "avg_reward":
        projected = max(-1.0, min(1.0, projected))
    elif metric == "avg_duration_ms":
        projected = max(0.0, projected)

    trend = _classify_trend(slope, metric)

    thresholds = ALERT_THRESHOLDS.get(metric, {})
    alert = False
    alert_reason = None
    if "below" in thresholds and projected < thresholds["below"]:
        alert = True
        alert_reason = f"projected {round(projected, 3)} < {thresholds['below']}"
    if "above" in thresholds and projected > thresholds["above"]:
        alert = True
        alert_reason = f"projected {round(projected, 1)} > {thresholds['above']}"

    result = {
        "metric":     metric,
        "window":     window,
        "horizon":    horizon_tasks,
        "samples":    len(series),
        "current":    round(current, 4),
        "slope":      round(slope, 6),
        "trend":      trend,
        "projected":  round(projected, 4),
        "confidence": _confidence(len(series)),
        "alert":      alert,
        "alert_reason": alert_reason,
        "built_at":   _now_iso(),
    }

    # persist
    data = _load(FORECASTS, {"version": 1, "forecasts": []})
    data.setdefault("forecasts", []).append(result)
    data["updated_at"] = _now_iso()
    _save(FORECASTS, data)

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--metric", required=True, choices=["success_rate", "avg_reward", "avg_duration_ms"])
    parser.add_argument("--horizon", type=int, default=10, help="how many tasks ahead to project")
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW, help="how many recent entries to fit")
    args = parser.parse_args(argv)

    result = forecast(args.metric, args.horizon, args.window)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
