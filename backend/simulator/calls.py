"""Emergency call and rescue request simulation.

The :class:`EmergencyCallSimulator` generates ``emergency_event`` dicts from a
set of known incident "hotspots" (geographic templates where flooding is most
likely).  Calls escalate in reported people and severity once the storm
intensifies, following a deterministic-but-noise-perturbed generator so stress
tests remain reproducible for a fixed seed.

Every emitted event is a canonical event dict ``{"type": "emergency_event",
"payload": {...}}`` consumable directly by
``backend.digital_twin.state_manager.apply_event``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.utils.logging import get_logger
from backend.utils.time import to_iso
from config.constants import IncidentPriority

logger = get_logger("simulator.calls")

#: Canonical event ``type`` emitted by the emergency call simulator.
EMERGENCY_EVENT_TYPE = "emergency_event"

#: Severity at which an incident is always considered ``CRITICAL``.
_CRITICAL_SEVERITY = 0.75


@dataclass(frozen=True)
class IncidentHotspot:
    """A geographic template for a likely emergency incident.

    All fields except the dynamic human/severity estimates are static; the
    generator perturbs people counts, priority and severity at call time.
    """

    hotspot_id: str
    incident_type: str
    geometry: tuple[float, float]        #: ``(lat, lon)`` epicentre
    description: str
    base_people: int
    base_severity: float


def _default_hotspots() -> List[IncidentHotspot]:
    """Return the built-in known flood incident hotspots around Kochi, Kerala."""
    return [
        IncidentHotspot(
            hotspot_id="HS-01",
            incident_type="Rescue Request",
            geometry=(9.9312, 76.2673),
            description="Low-lying residential area flooded; residents stranded above ground floor.",
            base_people=6,
            base_severity=0.6,
        ),
        IncidentHotspot(
            hotspot_id="HS-02",
            incident_type="Medical Emergency",
            geometry=(9.9400, 76.2800),
            description="Household member requires urgent evacuation to hospital.",
            base_people=2,
            base_severity=0.7,
        ),
        IncidentHotspot(
            hotspot_id="HS-03",
            incident_type="Road Blockage",
            geometry=(9.9300, 76.2600),
            description="Fallen tree and surface flooding blocking main road.",
            base_people=1,
            base_severity=0.5,
        ),
        IncidentHotspot(
            hotspot_id="HS-04",
            incident_type="Water Intrusion",
            geometry=(9.9657, 76.2427),
            description="Water entering ground-floor homes; residents need relocation.",
            base_people=4,
            base_severity=0.65,
        ),
        IncidentHotspot(
            hotspot_id="HS-05",
            incident_type="Vehicle Stranded",
            geometry=(9.9240, 76.2900),
            description="Vehicle stalled in rising water; occupants requiring rescue.",
            base_people=3,
            base_severity=0.55,
        ),
    ]


def _priority_from_severity(severity: float) -> IncidentPriority:
    """Map a severity score in ``[0, 1]`` to an :class:`IncidentPriority`."""
    if severity >= _CRITICAL_SEVERITY:
        return IncidentPriority.CRITICAL
    if severity >= 0.55:
        return IncidentPriority.HIGH
    if severity >= 0.35:
        return IncidentPriority.MEDIUM
    return IncidentPriority.LOW


class EmergencyCallSimulator:
    """Deterministic generator of citizen emergency calls from hotspots.

    Hotspots are visited cyclically (with mild geometric/attribute noise), so a
    fixed seed yields a repeatable sequence of ``emergency_event`` dicts.  Use
    :meth:`call_probability` to decide how often the engine generates a fresh
    call for a given storm intensity.
    """

    def __init__(
        self,
        seed: int = 7,
        hotspots: Optional[List[IncidentHotspot]] = None,
    ) -> None:
        """Configure the simulator.

        :param seed: RNG seed for reproducible call generation.
        :param hotspots: known incident hotspot templates. Defaults to the
            built-in Kochi hotspot set.
        """
        self._rng = random.Random(seed)
        self.hotspots: List[IncidentHotspot] = (
            list(hotspots) if hotspots else _default_hotspots()
        )
        self._sequence: int = 0

    # -------------------------------------------------------------- generators

    def generate_calls(self, now: datetime, incident_id: str) -> Dict[str, Any]:
        """Generate a single ``emergency_event`` for the next hotspot.

        :param now: timestamp attributed to the call.
        :param incident_id: unique identifier for the new incident.

        The generator cycles through the hotspots, jittering severity and the
        number of reported people around each template's base values.
        """
        hotspot = self.hotspots[self._sequence % len(self.hotspots)]
        self._sequence += 1

        severity = self._bounded(
            hotspot.base_severity + self._rng.uniform(0.0, 0.12)
        )
        reported_people = max(
            1, hotspot.base_people + self._rng.randint(0, 2)
        )
        latitude, longitude = self._jitter_point(hotspot.geometry)

        payload: Dict[str, Any] = {
            "incident_id": incident_id,
            "incident_type": hotspot.incident_type,
            "geometry": [[latitude, longitude]],
            "priority": _priority_from_severity(severity).value,
            "status": "ACTIVE",
            "description": hotspot.description,
            "reported_people": reported_people,
            "severity": severity,
            "source": "simulator",
            "created_at": to_iso(now),
        }
        return {"type": EMERGENCY_EVENT_TYPE, "payload": payload}

    def call_probability(
        self, intensity_mmh: float, base: float = 0.08, heavy: float = 0.85
    ) -> float:
        """Return the chance of receiving a new call at this rainfall intensity.

        Linearly interpolates from ``base`` (no storm) to ``heavy`` (extreme
        rainfall, mm/h).  Values are clamped to ``[0, 1]``.
        """
        if intensity_mmh >= 60.0:
            return min(1.0, heavy)
        if intensity_mmh <= 0.0:
            return max(0.0, base)
        scale = intensity_mmh / 60.0
        return max(0.0, min(1.0, base + (heavy - base) * scale))

    # -------------------------------------------------------------- internals

    def _jitter_point(self, point: tuple[float, float]) -> tuple[float, float]:
        """Perturb a hotspot point by a few arc-minutes (~hundreds of metres)."""
        lat, lon = point
        lat += (self._rng.random() - 0.5) * 0.006
        lon += (self._rng.random() - 0.5) * 0.006
        return (round(lat, 5), round(lon, 5))

    @staticmethod
    def _bounded(value: float) -> float:
        """Clamp a severity score into the inclusive ``[0, 1]`` range."""
        return max(0.0, min(1.0, value))


__all__ = ["IncidentHotspot", "EmergencyCallSimulator", "EMERGENCY_EVENT_TYPE"]