import io
import subprocess
from typing import Tuple, List, Dict, NamedTuple

from utils import process_timestamp_and_size

import numpy as np


class Packet(NamedTuple):
    timestamp: float
    size: int


def validate_parameters(
    min_coverage_seconds: float,
    max_gap_seconds: float,
) -> None:
    if not 0 < min_coverage_seconds <= 1:
        raise ValueError(
            f"min_coverage_seconds must be between 0 and 1, got {min_coverage_seconds}"
        )

    if not 0 < max_gap_seconds <= 1:
        raise ValueError(
            f"max_gap_seconds must be between 0 and 1, got {max_gap_seconds}"
        )


def calculate_bitrates(
    process: subprocess.Popen,
    use_dts: bool,
    output_unit: str,
    min_coverage_seconds: float = 0.9,
    max_gap_seconds: float = 0.1,
) -> Tuple[List[int], List[float], Dict]:
    """
    Calculate bitrates from packet timestamps and sizes.
    """
    if not process or not hasattr(process, "stdout"):
        raise ValueError("Invalid process object provided")

    valid_units = {"kbps", "mbps", "gbps"}
    if output_unit not in valid_units:
        raise ValueError(
            f"Invalid output unit '{output_unit}'. Must be one of: {valid_units}"
        )

    validate_parameters(min_coverage_seconds, max_gap_seconds)

    unit_multipliers = {
        "kbps": 0.001,
        "mbps": 0.000001,
        "gbps": 0.000000001,
    }

    packets: List[Packet] = []
    rejection_reasons: Dict[str, int] = {}
    total_bytes = 0

    for line in io.TextIOWrapper(process.stdout, encoding="utf-8"):
        if not line.strip():
            continue

        result = process_timestamp_and_size(line.strip().split(",", 2))

        if not result:
            rejection_reasons["invalid format"] = (
                rejection_reasons.get("invalid format", 0) + 1
            )
            continue

        timestamp, packet_size = result
        total_bytes += packet_size
        packets.append(Packet(timestamp, packet_size))

    if not packets:
        reasons = ", ".join(f"{k}: {v}" for k, v in rejection_reasons.items())
        raise ValueError(f"No valid packets found. Rejection reasons: {reasons}")

    # Sort timestamps in ascending order
    packets.sort(key=lambda x: x.timestamp)
    min_timestamp = packets[0].timestamp
    max_timestamp = packets[-1].timestamp

    # Group packets by second
    bytes_per_second = {}
    packets_per_second = {}
    timestamp_bounds_per_second = {}

    for packet in packets:
        second = int(packet.timestamp)
        bytes_per_second[second] = bytes_per_second.get(second, 0) + packet.size
        packets_per_second[second] = packets_per_second.get(second, 0) + 1

        if second not in timestamp_bounds_per_second:
            timestamp_bounds_per_second[second] = {
                "min": packet.timestamp,
                "max": packet.timestamp,
            }
        else:
            timestamp_bounds_per_second[second]["max"] = packet.timestamp

    duration = int(max_timestamp) - int(min_timestamp)
    # Round up to the next integer
    if max_timestamp > int(max_timestamp):
        duration += 1

    # Identify complete seconds
    complete_seconds = set()
    incomplete_reasons = {}

    all_seconds = sorted(bytes_per_second.keys())
    for i in range(len(all_seconds) - 1):
        current_second = all_seconds[i]
        next_second = all_seconds[i + 1]

        curr_bounds = timestamp_bounds_per_second[current_second]
        next_bounds = timestamp_bounds_per_second[next_second]

        coverage = abs(curr_bounds["max"] - curr_bounds["min"])
        gap = abs(next_bounds["min"] - curr_bounds["max"])

        if coverage >= min_coverage_seconds and gap < max_gap_seconds:
            complete_seconds.add(current_second)
        else:
            print(f"{next_bounds["min"]} to {next_bounds["max"]}")
            if coverage < min_coverage_seconds:
                incomplete_reasons[current_second] = (
                    f"insufficient coverage: {coverage:.3f}s"
                )
            else:
                incomplete_reasons[current_second] = f"gap too large: {gap:.3f}s"

    if not complete_seconds:
        reasons = "\n".join(f"Second {s}: {r}" for s, r in incomplete_reasons.items())
        raise ValueError(
            "No complete seconds found for bitrate calculation.\n"
            f"Total seconds: {len(all_seconds)}\n"
            f"Time range: {min_timestamp:.3f}s to {max_timestamp:.3f}s\n"
            f"Total packets: {len(packets)}\n"
            f"Reasons:\n{reasons}"
        )

    complete_seconds_list = sorted(complete_seconds)
    x_axis_values = complete_seconds_list

    bitrates = []
    for second in complete_seconds_list:
        bytes_this_second = bytes_per_second[second]
        bitrate = (bytes_this_second * 8) * unit_multipliers[output_unit]
        bitrates.append(bitrate)

    num_complete_seconds = len(complete_seconds)
    num_incomplete_seconds = duration - len(complete_seconds)

    data = {
        "mode": "DTS" if use_dts else "PTS",
        f"min_bitrate_{output_unit}": np.min(bitrates),
        f"mean_bitrate_{output_unit}": np.mean(bitrates),
        f"max_bitrate_{output_unit}": np.max(bitrates),
        "complete_seconds": num_complete_seconds,
        "num_incomplete_seconds": num_incomplete_seconds,
        "total_packets": len(packets),
        "total_bytes": total_bytes,
        "rejected_packets": sum(rejection_reasons.values()),
        "rejection_reasons": rejection_reasons,
        "incomplete_reasons": incomplete_reasons,
        "packets_per_second": {
            "min": min(packets_per_second[s] for s in complete_seconds),
            "max": max(packets_per_second[s] for s in complete_seconds),
            "avg": sum(packets_per_second[s] for s in complete_seconds)
            / len(complete_seconds),
        },
        "timing": {
            "first_timestamp": min_timestamp,
            "last_timestamp": max_timestamp,
        },
        "parameters": {
            "min_coverage_seconds": min_coverage_seconds,
            "max_gap_seconds": max_gap_seconds,
        },
    }

    if num_incomplete_seconds > 0:
        print(
            f"Found {num_incomplete_seconds} incomplete seconds that will be excluded from calculations. "
            f"Used {num_complete_seconds} complete seconds for bitrate calculations."
        )

        packets_excluded: List[Packet] = []

        for packet in packets:
            if packet.timestamp >= len(complete_seconds):
                packets_excluded.append(packet)

        unused_timestamp_range_min = packets_excluded[0].timestamp
        unused_timestamp_range_max = packets_excluded[-1].timestamp

        print(
            f"Unused {'DTS' if use_dts else 'PTS'} range: {unused_timestamp_range_min} to {unused_timestamp_range_max}"
        )

        data["unused_timestamp_range"] = (
            f"{unused_timestamp_range_min} to {unused_timestamp_range_max}"
        )

    return x_axis_values, bitrates, data
