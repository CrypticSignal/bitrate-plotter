import os
import subprocess

from ffmpeg import probe


class FileInfoProvider:
    def __init__(self, file_path):
        self._file_path = file_path

    def is_video(self):
        # This command will information about file's first stream.
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-threads",
            str(os.cpu_count()),
            "-show_streams",
            "-select_streams",
            "V",
            self._file_path,
        ]

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        return process.stdout.read().decode("utf-8")

    def get_duration(self):
        return float(probe(self._file_path)["format"]["duration"])

    def get_number_of_packets(self, stream_specifier):
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            stream_specifier,
            "-count_packets",
            "-show_entries",
            "stream=nb_read_packets",
            "-of",
            "default=nokey=1:noprint_wrappers=1",
            self._file_path,
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        return int(process.stdout.read().decode())


class VideoInfoProvider:
    def __init__(self, video_path):
        self._video_path = video_path

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
    if len(parts) < 2:
        return None
    try:
        timestamp = float(parts[0])
        packet_size = int(parts[1])
        return timestamp, packet_size
    except (ValueError, IndexError, OverflowError):
        return None
