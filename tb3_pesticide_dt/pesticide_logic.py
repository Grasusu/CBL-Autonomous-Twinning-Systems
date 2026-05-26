#!/usr/bin/env python3
"""Small helpers shared by the pesticide inspection DT nodes."""

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence


@dataclass(frozen=True)
class PlantZone:
    zone_id: str
    name: str
    x: float
    y: float
    yaw: float
    residue_index: float = 0.0
    expected_status: str = "OK"


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_angle(angle: float) -> float:
    """Normalize an angle to [-pi, pi]."""
    return math.atan2(math.sin(angle), math.cos(angle))


def quaternion_to_yaw(x: float, y: float, z: float, w: float) -> float:
    """Return yaw from a geometry_msgs Quaternion-like tuple."""
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


def classify_residue(residue_index: float, threshold: float) -> str:
    if residue_index >= threshold:
        return "OVERUSE"
    return "OK"


def coerce_list(values: Iterable, cast, fallback: Sequence) -> List:
    if values is None:
        return list(fallback)
    return [cast(value) for value in values]


def build_zones(
    zone_ids: Sequence[str],
    zone_names: Sequence[str],
    zone_x: Sequence[float],
    zone_y: Sequence[float],
    zone_yaw: Sequence[float],
    residue_indices: Sequence[float],
    expected_statuses: Sequence[str],
) -> List[PlantZone]:
    lengths = {
        len(zone_ids),
        len(zone_names),
        len(zone_x),
        len(zone_y),
        len(zone_yaw),
        len(residue_indices),
        len(expected_statuses),
    }
    if len(lengths) != 1:
        raise ValueError(
            "Plant-zone parameter arrays must have equal length: "
            f"ids={len(zone_ids)} names={len(zone_names)} x={len(zone_x)} "
            f"y={len(zone_y)} yaw={len(zone_yaw)} residues={len(residue_indices)} "
            f"statuses={len(expected_statuses)}"
        )

    zones: List[PlantZone] = []
    for i, zone_id in enumerate(zone_ids):
        zones.append(
            PlantZone(
                zone_id=str(zone_id),
                name=str(zone_names[i]),
                x=float(zone_x[i]),
                y=float(zone_y[i]),
                yaw=float(zone_yaw[i]),
                residue_index=float(residue_indices[i]),
                expected_status=str(expected_statuses[i]).upper(),
            )
        )
    return zones

