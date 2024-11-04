from dataclasses import dataclass
import io
from typing import List, Tuple, TextIO, NamedTuple

from utils import append_to_file

import numpy as np


@dataclass
class Frame:
    time: float  # PTS or DTS time
    size: float  # Size in megabits
    flags: str  # Frame flag (e.g. 'K__')

    @property
    def is_keyframe(self) -> bool:
        return "K" in self.flags


class GOPStats(NamedTuple):
    duration: float
    size: float
    bitrate: float
    frame_count: int
    avg_frame_size: float


class GOP:
    def __init__(self, start_time: float, frames: List[Frame]):
        self.start_time = start_time
        self.frames = frames

    @property
    def end_time(self) -> float:
        return self.frames[-1].time

    @property
    def size(self) -> float:
        return sum(frame.size for frame in self.frames)

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def avg_frame_size(self) -> float:
        return self.size / self.frame_count

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
            frame_count=self.frame_count,
            avg_frame_size=self.avg_frame_size,
        )


class VideoStats:
    def __init__(self, frames: List[Frame], gops: List[GOP], framerate: float):
        self.frames = frames
        self.gops = gops
        self.framerate = framerate
        self.gop_stats = [gop.calculate_stats(framerate) for gop in gops]

    @property
    def first_time(self) -> float:
        return self.frames[0].time if self.frames else 0

    @property
    def final_time(self) -> float:
        return self.frames[-1].time if self.frames else 0

    @property
    def total_frames(self) -> int:
        return len(self.frames)

    def calculate_time_intervals(self) -> List[float]:
        """Calculate time intervals between consecutive frames"""
        return [
            self.frames[i + 1].time - self.frames[i].time
            for i in range(len(self.frames) - 1)
            if self.frames[i + 1].time - self.frames[i].time > 0
        ]

    def get_frame_size_range(self) -> Tuple[float, float]:
        """Get min and max frame sizes"""
        sizes = [frame.size for frame in self.frames]
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
            "avg_frames": np.mean([s.frame_count for s in self.gop_stats]),
        }


def calculate_gop_bitrates(
    process: TextIO,
    progress_bar: any,
    task_1: str,
    task_2: str,
    framerate: float,
    number_of_frames: int,
    data_file: str,
    use_dts: bool = False,
) -> Tuple[List[float], List[float]]:
    """
    Calculate bitrates for each Group of Pictures (GOP) in a video stream.

    Args:
        process: Subprocess stdout containing frame data in CSV format (time,size,flags)
        progress_bar: Progress bar object for updating progress
        task_1: Task identifier for frame collection progress
        task_2: Task identifier for GOP analysis progress
        framerate: Video framerate in frames per second
        number_of_frames: Total number of frames expected
        data_file: Path to file for writing statistics
        use_dts: If True, use DTS for calculations. If False, use PTS (default)

    Returns:
        gop_end_times: List of GOP end times in seconds
        gop_bitrates: List of GOP bitrates in Mbps

    Raises:
        RuntimeError: If no valid frames are found or other processing errors occur
        ValueError: If GOP duration is invalid
    """

    def collect_frames() -> List[Frame]:
        """Collect and parse all frames from the input."""
        frames = []
        total_frames = 0

        for line in io.TextIOWrapper(process.stdout, encoding="utf-8"):
            total_frames += 1
            progress_bar.update(task_1, completed=total_frames)

            try:
                parts = line.strip().split(",")
                if len(parts) != 3:
                    print(f"Warning: Invalid line format: {line}")
                    continue

                time = float(parts[0])
                size = (int(parts[1]) * 8) / 1_000_000  # Convert to megabits
                flags = parts[2]

                frames.append(Frame(time, size, flags))

            except (ValueError, IndexError) as e:
                append_to_file(
                    data_file,
                    f"Warning: Error processing frame {total_frames}: {str(e)}",
                )

        if not frames:
            raise RuntimeError("No valid frames found in input")

        return sorted(frames, key=lambda f: f.time)

    def process_gops(frames: List[Frame]) -> List[GOP]:
        """Process frames into GOPs."""
        gops = []
        current_gop_frames = []
        first_keyframe_found = False

        for frame_number, frame in enumerate(frames, start=1):
            progress_bar.update(task_2, completed=frame_number)

            if frame.is_keyframe:
                if first_keyframe_found and current_gop_frames:
                    gops.append(GOP(current_gop_frames[0].time, current_gop_frames))
                first_keyframe_found = True
                current_gop_frames = [frame]
            elif first_keyframe_found:
                current_gop_frames.append(frame)

        # Add final GOP
        if first_keyframe_found and current_gop_frames:
            gops.append(GOP(current_gop_frames[0].time, current_gop_frames))

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
        append_to_file(data_file, f"\nFrames: {stats.frame_count}")
        append_to_file(
            data_file, f"\nAverage frame size: {stats.avg_frame_size:.3f} Megabits\n\n"
        )

    timing_type = "DTS" if use_dts else "PTS"

    try:
        # Collect and process frames
        frames = collect_frames()
        gops = process_gops(frames)

        if not gops:
            print("\nNo GOPs found in video!")
            return [], []

        # Calculate statistics
        video_stats = VideoStats(frames, gops, framerate)
        time_intervals = video_stats.calculate_time_intervals()
        gop_stats_range = video_stats.get_gop_stats_range()
        min_frame_size, max_frame_size = video_stats.get_frame_size_range()

        # Write individual GOP statistics
        for i, (gop, stats) in enumerate(zip(gops, video_stats.gop_stats), 1):
            write_gop_stats(i, gop, stats)

        # Write summary statistics
        append_to_file(data_file, "Timestamp Statistics:")
        append_to_file(
            data_file,
            f"\nVideo time range: {video_stats.first_time:.3f}s to {video_stats.final_time:.3f}s",
        )

        append_to_file(data_file, "\n\nGOP Statistics:")
        append_to_file(data_file, f"\nGOP count: {len(gops)}")
        append_to_file(
            data_file, f"\nAverage frames per GOP: {gop_stats_range['avg_frames']:.1f}"
        )
        append_to_file(
            data_file,
            f"\nGOP duration range: {gop_stats_range['duration'][0]:.3f}s to {gop_stats_range['duration'][1]:.3f}s",
        )
        append_to_file(
            data_file, f"\nAverage GOP duration: {gop_stats_range['duration'][2]:.3f}s"
        )
        append_to_file(
            data_file,
            f"\nGOP size range: {gop_stats_range['size'][0]:.2f} to {gop_stats_range['size'][1]:.2f} Megabits",
        )
        append_to_file(
            data_file,
            f"\nGOP bitrate range: {gop_stats_range['bitrate'][0]:.2f} to {gop_stats_range['bitrate'][1]:.2f} Mbps",
        )
        append_to_file(
            data_file,
            f"\nAverage GOP bitrate: {gop_stats_range['bitrate'][2]:.2f} Mbps",
        )

        # Frame statistics
        append_to_file(data_file, "\n\nFrame Statistics:")
        append_to_file(
            data_file,
            f"\nFrame size range: {min_frame_size:.6f} to {max_frame_size:.6f} Megabits",
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
                    f"! {timing_type} intervals are inconsistent. Min interval: {min_frame_size} | Max interval: "
                )

        min_duration, max_duration = gop_stats_range["duration"][:2]
        if max_duration == min_duration:
            print("✓ GOP durations are consistent")
        else:
            print(
                f"! GOP durations are inconsistent:\nMin Duration: {min_duration}\nMax Duration: {max_duration}"
            )

        expected_frames = round(framerate * (number_of_frames / framerate))
        if video_stats.total_frames == expected_frames:
            print("✓ Frame count matches expected count")
        else:
            print(
                f"! Frame count differs from expected ({video_stats.total_frames} vs {expected_frames})"
            )

        gop_end_times = [gop.end_time for gop in gops]
        gop_bitrates = [stats.bitrate for stats in video_stats.gop_stats]

        return gop_end_times, gop_bitrates

    except Exception as e:
        raise RuntimeError(f"Error processing video data: {str(e)}")
