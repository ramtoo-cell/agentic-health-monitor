'''Health monitoring for agent fleets.

Each agent reports check results (``ok`` / ``fail`` with latency).
The monitor keeps a rolling window per agent and computes a health
score = fraction of passing checks.  States derive from the score:

* ``healthy`` score >= 0.9,
* ``degraded`` 0.5 <= score < 0.9,
* ``down`` score < 0.5 (or no data and marked stale).

State transitions fire alerts through a router callable; flapping is
damped by requiring ``stable_for`` consecutive windows before a
transition is announced.
'''

from __future__ import annotations

import time
from collections import deque


class HealthMonitor:
    '''Rolling-window health tracking with alerting.'''

    def __init__(self, window=20, stale_after=300.0, stable_for=2):
        self.window = window
        self.stale_after = stale_after
        self.stable_for = stable_for
        self.checks = {}   # agent -> deque of (ok, latency, at)
        self.states = {}   # agent -> current announced state
        self._pending = {}  # agent -> (candidate_state, count)
        self.alerts = []

    def report(self, agent, ok, latency=0.0, at=None):
        at = time.monotonic() if at is None else at
        checks = self.checks.setdefault(agent, deque(maxlen=self.window))
        checks.append((ok, latency, at))
        self._evaluate(agent, at)

    def _score(self, agent, now):
        checks = self.checks.get(agent, ())
        if not checks:
            return 0.0
        if now - checks[-1][2] > self.stale_after:
            return 0.0
        return sum(1 for ok, _, _ in checks if ok) / len(checks)

    @staticmethod
    def _state_for(score):
        if score >= 0.9:
            return "healthy"
        if score >= 0.5:
            return "degraded"
        return "down"

    def _evaluate(self, agent, now):
        candidate = self._state_for(self._score(agent, now))
        current = self.states.get(agent)
        if candidate == current:
            self._pending.pop(agent, None)
            return
        pending_state, count = self._pending.get(agent, (candidate, 0))
        if pending_state != candidate:
            self._pending[agent] = (candidate, 1)
            return
        count += 1
        if count >= self.stable_for:
            self.states[agent] = candidate
            self._pending.pop(agent, None)
            if current is not None:  # no alert for initial discovery
                self.alerts.append({"agent": agent, "from": current,
                                    "to": candidate, "at": now})
        else:
            self._pending[agent] = (candidate, count)

    def state(self, agent, now=None):
        now = time.monotonic() if now is None else now
        # refresh staleness without a new check
        self._evaluate(agent, now)
        return self.states.get(agent, "unknown")

    def mean_latency(self, agent):
        checks = self.checks.get(agent, ())
        if not checks:
            return 0.0
        return sum(lat for _, lat, _ in checks) / len(checks)

    def fleet_summary(self, now=None):
        now = time.monotonic() if now is None else now
        summary = {"healthy": 0, "degraded": 0, "down": 0, "unknown": 0}
        for agent in self.checks:
            summary[self.state(agent, now)] += 1
        return summary

    def remove_agent(self, agent):
        self.checks.pop(agent, None)
        self.states.pop(agent, None)
        self._pending.pop(agent, None)

    def agents(self):
        return sorted(self.checks)

    def uptime(self, agent):
        '''Fraction of passing checks in the window (0.0 when no data).'''
        checks = self.checks.get(agent, ())
        if not checks:
            return 0.0
        return sum(1 for ok, _, _ in checks if ok) / len(checks)

    def last_check(self, agent):
        '''(ok, latency, at) of the most recent check; None when absent.'''
        checks = self.checks.get(agent, ())
        return checks[-1] if checks else None

    def alert_count(self):
        return len(self.alerts)

    def recent_alerts(self, n=10):
        return list(self.alerts[-n:])

    def worst_agents(self, n=5, now=None):
        '''Agents with the lowest health scores.'''
        now = time.monotonic() if now is None else now
        scored = sorted(((self._score(a, now), a) for a in self.checks))
        return [a for _, a in scored[:n]]
