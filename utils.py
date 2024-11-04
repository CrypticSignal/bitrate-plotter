import os
import subprocess

from ffmpeg import probe


class FileInfoProvider:
    def __init__(self, file_path):
        self._file_path = file_path

    def first_stream_info(self):
        # This command will information about file's first stream.
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-threads",
            str(os.cpu_count()),
            "-show_streams",
            "-select_streams",
            "0",
            self._file_path,
        ]

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        return process.stdout.read().decode("utf-8")

    def get_duration(self):
        return float(probe(self._file_path)["format"]["duration"])


class VideoInfoProvider:
    def __init__(self, video_path):
        self._video_path = video_path

    def get_number_of_frames(self):
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-threads",
            str(os.cpu_count()),
            "-select_streams",
            "V:0",
            "-count_packets",
            "-show_entries",
            "stream=nb_read_packets",
            "-of",
            "csv=p=0",
            self._video_path,
        ]
        process = subprocess.run(cmd, capture_output=True)
        return int(process.stdout.decode("utf-8"))

    def get_video_bitrate(self):
        bitrate = probe(self._video_path)["format"]["bit_rate"]

        return f"{(int(bitrate) / 1_000_000)} Mbps"

    def get_framerate_fraction(self):
        r_frame_rate = [
            stream
            for stream in probe(self._video_path)["streams"]
            if stream["codec_type"] == "video"
        ][0]["r_frame_rate"]

        return r_frame_rate

    def get_average_framerate(self):
        return [
            stream
            for stream in probe(self._video_path)["streams"]
            if stream["codec_type"] == "video"
        ][0]["avg_frame_rate"]

    def get_framerate_number(self):
        numerator, denominator = self.get_framerate_fraction().split("/")

        return int(numerator) / int(denominator)

    def is_constant_framerate(self):
        return self.get_framerate_fraction() == self.get_average_framerate()

    def is_integer_framerate(self):
        return self.get_framerate_number().is_integer()


def line():
    width, _ = os.get_terminal_size()
    print("-" * width)


def append_to_file(filename, data):
    with open(filename, "a") as f:
        f.write(data)


def process_timestamp_and_size(parts):
    """Helper function to process and validate timestamp and size."""
    if len(parts) < 2:
        return None
    try:
        timestamp = float(parts[0])
        packet_size = int(parts[1])
        if packet_size < 0:  # Allow negative timestamps
            return None
        if abs(timestamp) > 1e6:  # Arbitrary large value check
            return None
        return timestamp, packet_size
    except (ValueError, IndexError, OverflowError):
        return None


def convert_to_mbits(bytes_size):
    """Convert bytes to megabits."""
    try:
        return (bytes_size * 8) / 1_000_000
    except OverflowError:
        raise ValueError(f"Packet size too large to process: {bytes_size}")


def get_second(
    use_dts,
    is_constant_framerate,
    is_integer_framerate,
    timestamp,
    frame_number,
    framerate,
    initial_timestamp,
):
    """Calculate the current second based on timing mode."""
    try:
        if use_dts and is_constant_framerate and is_integer_framerate:
            # Subtract 1 from frame_number to get correct second
            return (frame_number - 1) // int(framerate)
        return int(timestamp - initial_timestamp)
    except (OverflowError, ValueError):
        raise ValueError(
            f"Invalid timestamp calculation: {timestamp} - {initial_timestamp}"
        )
