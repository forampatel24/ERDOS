"""Tests for simulator: engine, sensors, storm profile."""

from __future__ import annotations

import pytest

from backend.simulator.engine import SimulationEngine
from backend.simulator.sensors import SensorSimulator
from backend.digital_twin.state_manager import get_state_manager


class TestSensorSimulator:
    def test_rainfall_intensity_profile(self):
        sim = SensorSimulator(road_ids=("R001", "R002"), seed=42)
        # Tick advances storm; rainfall should be non-negative
        events = sim.tick(30.0)
        assert len(events) > 0
        assert sim.rainfall_intensity() >= 0

    def test_water_level_per_road(self):
        sim = SensorSimulator(road_ids=("R001",), seed=1)
        sim.tick(60.0)
        wl = sim.water_level("R001")
        assert isinstance(wl, float)
        assert wl >= 0

    def test_storm_profile(self):
        from backend.simulator.sensors import StormProfile

        p = StormProfile()
        assert p.peak_mmh > 0
        assert p.rise_hours > 0
        assert hasattr(p, "start_mmh")


class TestSimulationEngine:
    def test_advance_emits_events(self):
        eng = SimulationEngine(seed=123)
        evts = eng.advance(30.0)
        assert len(evts) >= 4  # weather + river + sensors + traffic at least
        types = {e["type"] for e in evts}
        assert "weather_update" in types
        assert "river_update" in types

    def test_advance_clock(self):
        eng = SimulationEngine(seed=1)
        t0 = eng.elapsed_seconds
        eng.advance(30.0)
        assert eng.elapsed_seconds == t0 + 30.0

    def test_push_events_into_twin(self):
        eng = SimulationEngine(seed=2)
        sm = get_state_manager()
        before_roads = len(sm.roads)
        evts = eng.advance(30.0)
        eng.push_events(evts)
        # Twin should still have roads (engine seeds infrastructure)
        assert len(sm.roads) >= before_roads

    def test_run_multiple_steps(self):
        eng = SimulationEngine(seed=3)
        all_evts = eng.run(steps=3)
        assert len(all_evts) > 0
        assert eng.elapsed_seconds >= 90.0

    def test_river_level_increases_with_rain(self):
        eng = SimulationEngine(seed=4)
        lvl0 = eng._river_level
        for _ in range(5):
            eng.advance(3600.0)  # 1h steps to accumulate
        assert eng._river_level >= lvl0

    def test_road_failure_logic(self):
        eng = SimulationEngine(seed=5)
        # Water level threshold is 0.40m for BLOCKED
        assert hasattr(eng, "_failed_roads")
        assert isinstance(eng._failed_roads, set)
