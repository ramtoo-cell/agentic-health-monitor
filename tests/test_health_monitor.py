'''Tests for the health monitor.'''

import unittest

from src.health_monitor import HealthMonitor


class HealthMonitorTests(unittest.TestCase):
    def test_healthy(self):
        m = HealthMonitor(stable_for=1)
        for _ in range(10):
            m.report("a", True, at=1.0)
        self.assertEqual(m.state("a", now=2.0), "healthy")

    def test_degraded(self):
        m = HealthMonitor(stable_for=1)
        for i in range(10):
            m.report("a", i % 2 == 0, at=1.0)
        self.assertEqual(m.state("a", now=2.0), "degraded")

    def test_down(self):
        m = HealthMonitor(stable_for=1)
        for _ in range(10):
            m.report("a", False, at=1.0)
        self.assertEqual(m.state("a", now=2.0), "down")

    def test_unknown_no_data(self):
        m = HealthMonitor()
        self.assertEqual(m.state("ghost"), "unknown")

    def test_stale_is_down(self):
        m = HealthMonitor(stable_for=1, stale_after=10.0)
        for _ in range(10):
            m.report("a", True, at=0.0)
        self.assertEqual(m.state("a", now=100.0), "down")

    def test_flap_damping(self):
        m = HealthMonitor(stable_for=3)
        for _ in range(10):
            m.report("a", True, at=1.0)
        self.assertEqual(m.state("a", now=2.0), "healthy")
        m.report("a", False, at=3.0)  # single blip
        m.report("a", True, at=4.0)
        self.assertEqual(m.state("a", now=5.0), "healthy")
        self.assertEqual(m.alerts, [])

    def test_transition_alert(self):
        m = HealthMonitor(window=10, stable_for=1)
        for _ in range(10):
            m.report("a", True, at=1.0)
        for _ in range(10):
            m.report("a", False, at=2.0)
        alert = m.alerts[-1]
        self.assertEqual(alert["agent"], "a")

    def test_mean_latency(self):
        m = HealthMonitor()
        m.report("a", True, latency=0.2, at=1.0)
        m.report("a", True, latency=0.4, at=1.0)
        self.assertAlmostEqual(m.mean_latency("a"), 0.3)

    def test_fleet_summary(self):
        m = HealthMonitor(stable_for=1)
        for _ in range(10):
            m.report("a", True, at=1.0)
            m.report("b", False, at=1.0)
        summary = m.fleet_summary(now=2.0)
        self.assertEqual(summary["healthy"], 1)

    def test_window_bounds_memory(self):
        m = HealthMonitor(window=5, stable_for=1)
        for _ in range(100):
            m.report("a", True, at=1.0)
        self.assertLessEqual(len(m.checks["a"]), 5)

class HealthMonitorExtraTests(unittest.TestCase):
    def _monitor(self):
        m = HealthMonitor(window=10, stale_after=1000.0, stable_for=1)
        for i in range(10):
            m.report("a", ok=(i < 9), latency=0.1, at=float(i))
        for i in range(10):
            m.report("b", ok=True, latency=0.5, at=float(i))
        return m

    def test_remove_agent(self):
        m = HealthMonitor()
        m.report("a", True, at=1.0)
        m.remove_agent("a")
        self.assertEqual(m.agents(), [])
        # forgotten agents read like never-seen ones
        self.assertEqual(m.state("a"), "unknown")

    def test_agents(self):
        self.assertEqual(self._monitor().agents(), ["a", "b"])

if __name__ == "__main__":
    unittest.main()
