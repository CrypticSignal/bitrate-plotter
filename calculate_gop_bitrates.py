from dataclasses import dataclass
import io
from textwrap import dedent
from typing import List, Tuple, TextIO, NamedTuple

from utils import append_to_file

import numpy as np


@dataclass
class Packet:
    time: float  # PTS or DTS time
    size: float  # Size in megabits
    flags: str  # Packet flag (e.g. 'K__')

    @property
    def is_keyframe(self) -> bool:
        return "K" in self.flags


class GOPStats(NamedTuple):
    duration: float
    size: float
    bitrate: float
    packet_count: int
    avg_packet_size: float


class GOP:
    def __init__(self, start_time: float, packets: List[Packet]):
        self.start_time = start_time
        self.packets = packets

    @property
    def end_time(self) -> float:
        return self.packets[-1].time

    @property
    def size(self) -> float:
        return sum(packet.size for packet in self.packets)

    @property
    def packet_count(self) -> int:
        return len(self.packets)

    @property
    def avg_packet_size(self) -> float:
        return self.size / self.packet_count

    def calculate_stats(self, framerate: float) -> GOPStats:
        """Calculate GOP statistics"""
        duration = self.end_time - self.start_time + (1 / framerate)
        if duration <= 0:
            raise ValueError(f"Invalid GOP duration: {duration:.3f}s")
        bitrate = self.size / duration
        return GOPStats(
            duration=duration,
            size=self.size,
            bitrate=bitrate,
            packet_count=self.packet_count,
            avg_packet_size=self.avg_packet_size,
        )


class VideoStats:
    def __init__(self, packets: List[Packet], gops: List[GOP], framerate: float):
        self.packets = packets
        self.gops = gops
        self.framerate = framerate
        self.gop_stats = [gop.calculate_stats(framerate) for gop in gops]

    @property
    def first_time(self) -> float:
        return self.packets[0].time if self.packets else 0

    @property
    def final_time(self) -> float:
        return self.packets[-1].time if self.packets else 0

    @property
    def total_packets(self) -> int:
        return len(self.packets)

    def calculate_time_intervals(self) -> List[float]:
        """Calculate time intervals between consecutive packets"""
        return [
            self.packets[i + 1].time - self.packets[i].time
            for i in range(len(self.packets) - 1)
            if self.packets[i + 1].time - self.packets[i].time > 0
        ]

    def get_packet_size_range(self) -> Tuple[float, float]:
        """Get min and max packet sizes"""
        sizes = [packet.size for packet in self.packets]
        return np.min(sizes), np.max(sizes)

    def get_gop_stats_range(self) -> dict:
        """Calculate min/max/avg of various GOP statistics"""
        if not self.gop_stats:
            return {}

        return {
            "duration": (
                np.min([s.duration for s in self.gop_stats]),
                np.max([s.duration for s in self.gop_stats]),
                np.mean([s.duration for s in self.gop_stats]),
            ),
            "size": (
                np.min([s.size for s in self.gop_stats]),
                np.max([s.size for s in self.gop_stats]),
                np.mean([s.size for s in self.gop_stats]),
            ),
            "bitrate": (
                np.min([s.bitrate for s in self.gop_stats]),
                np.max([s.bitrate for s in self.gop_stats]),
                np.mean([s.bitrate for s in self.gop_stats]),
            ),
            "avg_packets": np.mean([s.packet_count for s in self.gop_stats]),
        }


def calculate_gop_bitrates(
    process: TextIO,
    progress_bar: any,
    task_1: str,
    task_2: str,
    framerate,
    data_file: str,
    use_dts: bool = False,
) -> Tuple[List[float], List[float]]:
    """
    Calculate bitrates for each Group of Pictures (GOP) in a video stream.

    Args:
        process: Subprocess stdout containing frame data in CSV format (time,size,flags)
        progress_bar: Progress bar object for updating progress
        task_1: Task identifier for packet collection progress
        task_2: Task identifier for GOP analysis progress
        framerate: Video framerate in packets per second
        number_of_packets: Total number of packets expected
        data_file: Path to file for writing statistics
        use_dts: If True, use DTS for calculations. If False, use PTS (default)

    Returns:
        gop_end_times: List of GOP end times in seconds
        gop_bitrates: List of GOP bitrates in Mbps

    Raises:
        RuntimeError: If no valid packets are found or other processing errors occur
        ValueError: If GOP duration is invalid
    """

    def collect_packets() -> List[Packet]:
        """Collect and parse all packets from the input."""
        packets = []
        total_packets = 0

        for line in io.TextIOWrapper(process.stdout, encoding="utf-8"):
            total_packets += 1
            progress_bar.update(task_1, completed=total_packets)

            try:
                parts = line.strip().split(",")
                if len(parts) != 3:
                    print(f"Warning: Invalid line format: {line}")
                    continue

                time = float(parts[0])
                size = (int(parts[1]) * 8) / 1_000_000  # Convert to megabits
                flags = parts[2]

                packets.append(Packet(time, size, flags))

            except (ValueError, IndexError) as e:
                append_to_file(
                    data_file,
                    f"Warning: Error processing frame {total_packets}: {str(e)}",
                )

        if not packets:
            raise RuntimeError("No valid packets found in input")

        return sorted(packets, key=lambda f: f.time)

    def process_gops(packets: List[Packet]) -> List[GOP]:
        """Process packets into GOPs."""
        gops = []
        current_gop_packets = []
        first_keyframe_found = False

        for packet_number, frame in enumerate(packets, start=1):
            progress_bar.update(task_2, completed=packet_number)

            if frame.is_keyframe:
                if first_keyframe_found and current_gop_packets:
                    gops.append(GOP(current_gop_packets[0].time, current_gop_packets))
                first_keyframe_found = True
                current_gop_packets = [frame]
            elif first_keyframe_found:
                current_gop_packets.append(frame)

        # Add final GOP
        if first_keyframe_found and current_gop_packets:
            gops.append(GOP(current_gop_packets[0].time, current_gop_packets))

        return gops

    def write_gop_stats(gop_index: int, gop: GOP, stats: GOPStats):
        """Write statistics for a single GOP"""
        prefix = "Final GOP" if gop_index == len(gops) else "GOP"
        append_to_file(data_file, f"{prefix} {gop_index} statistics:")
        append_to_file(data_file, f"\nStart {timing_type}: {gop.start_time:.3f}s")
        append_to_file(data_file, f"\nEnd {timing_type}: {gop.end_time:.3f}s")
        append_to_file(data_file, f"\nDuration: {stats.duration:.3f}s")
        append_to_file(data_file, f"\nSize: {stats.size:.2f} Megabits")
        append_to_file(data_file, f"\nBitrate: {stats.bitrate:.2f} Mbps")
        append_to_file(data_file, f"\nPackets: {stats.packet_count}")
        append_to_file(
            data_file, f"\nAverage frame size: {stats.avg_packet_size:.3f} Megabits\n\n"
        )

    timing_type = "DTS" if use_dts else "PTS"

    try:
        # Collect and process packets
        packets = collect_packets()
        gops = process_gops(packets)

        if not gops:
            print("\nNo GOPs found in video!")
            return [], []

        # Calculate statistics
        video_stats = VideoStats(packets, gops, framerate)
        time_intervals = video_stats.calculate_time_intervals()
        gop_stats_range = video_stats.get_gop_stats_range()
        min_packet_size, max_packet_size = video_stats.get_packet_size_range()

        # Write individual GOP statistics
        for i, (gop, stats) in enumerate(zip(gops, video_stats.gop_stats), 1):
            write_gop_stats(i, gop, stats)

        # Write summary statistics
        append_to_file(data_file, "Timestamp Statistics:")
        append_to_file(
            data_file,
            f"\nVideo time range: {video_stats.first_time:.3f}s to {video_stats.final_time:.3f}s",
        )

        gop_stats_text = dedent(
            f"""
            GOP Statistics:
            
            GOP count: {len(gops)}
            Average number of packets per GOP: {gop_stats_range['avg_packets']:.1f}
            GOP duration range: {gop_stats_range['duration'][0]:.3f}s to {gop_stats_range['duration'][1]:.3f}s
            Average GOP duration: {gop_stats_range['duration'][2]:.3f}s
            GOP size range: {gop_stats_range['size'][0]:.2f} to {gop_stats_range['size'][1]:.2f} Megabits
            GOP bitrate range: {gop_stats_range['bitrate'][0]:.2f} to {gop_stats_range['bitrate'][1]:.2f} Mbps
            Average GOP bitrate: {gop_stats_range['bitrate'][2]:.2f} Mbps
            """
        )

        print(gop_stats_text)
        append_to_file(data_file, gop_stats_text)

        # Packet statistics
        append_to_file(data_file, "\n\nPacket Statistics:")
        append_to_file(
            data_file,
            f"\Packet size range: {min_packet_size:.6f} to {max_packet_size:.6f} Megabits",
        )

        if time_intervals:
            min_interval = np.min(time_intervals)
            max_interval = np.max(time_intervals)
            avg_interval = np.mean(time_intervals)

            append_to_file(
                data_file,
                f"\n{timing_type} interval range (non-zero): {min_interval:.6f}s to {max_interval:.6f}s",
            )
            append_to_file(
                data_file,
                f"\nAverage {timing_type} interval (non-zero): {avg_interval:.6f}s",
            )

        if len(time_intervals) > 0:
            avg_interval = np.mean(time_intervals)
            if abs(avg_interval == (1 / framerate)) < 0.000_000_001:
                print(f"✓ Average {timing_type} interval matches expected frame rate")
            else:
                print(
                    f"! Average {timing_type} interval ({avg_interval}s) differs from expected ({1/framerate}s)"
                )

            if abs(max_interval - min_interval) < 0.001:
                print(f"✓ {timing_type} intervals are consistent")
            else:
                print(
                    f"! {timing_type} intervals are inconsistent. Min interval: {min_interval} | Max interval: {max_interval}"
                )

        min_duration, max_duration = gop_stats_range["duration"][:2]
        if max_duration == min_duration:
            print("✓ GOP durations are consistent")
        else:
            print(
                f"[Info] GOP durations are inconsistent:\nMin GOP Duration: {min_duration}\nMax GOP Duration: {max_duration}"
            )

        gop_end_times = [gop.end_time for gop in gops]
        gop_bitrates = [stats.bitrate for stats in video_stats.gop_stats]

        return gop_end_times, gop_bitrates

    except Exception as e:
        raise RuntimeError(f"Error processing video data: {str(e)}")
