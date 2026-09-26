# Health Monitor for Agent Fleets

Health monitoring for agent fleets: periodic checks, rolling health scores, degraded-state detection, and alert routing on state changes.

**Stack:** Python 3.12 · stdlib only · unittest

## Problem statement

Each agent reports check results (`ok` / `fail` with latency). The monitor keeps a rolling window per agent and computes a health score = fraction of passing checks.  States derive from the score:

## Design decisions

- `healthy` score >= 0.9,
- `degraded` 0.5 <= score < 0.9,
- `down` score < 0.5 (or no data and marked stale).
- State transitions fire alerts through a router callable; flapping is damped by requiring `stable_for` consecutive windows before a transition is announced.

## Usage example

```python
from src.health_monitor import HealthMonitor

m = HealthMonitor()
for _ in range(10):
    m.report("worker-1", True, latency=0.1)
print(m.state("worker-1"))  # healthy
```

## Layout

- `README.md`
- `src/health_monitor.py`
- `tests/test_health_monitor.py`
- `LICENSE`
- `.gitignore`

## Setup

No third-party dependencies — Python 3.11+ standard library only.

```bash
cd agentic-health-monitor
python -m unittest discover -s tests -v
```

## License

MIT — see [LICENSE](LICENSE).
