import csv
from dataclasses import dataclass
from fractions import Fraction
import io
import json
import math
import shutil
import subprocess


def frame_rate(value):
    try:
        rate = float(Fraction(str(value)))
        return rate if math.isfinite(rate) and rate > 0 else 0.0
    except (ValueError, ZeroDivisionError, TypeError):
        return 0.0


@dataclass
class PacketRecord:
    time: float
    size: int  # bytes
    duration: float
    keyframe: bool


def parse_packet(line, use_dts=False, framerate=0):
    """Read keyed FFprobe compact output; tolerate legacy timestamp,size[,flags] CSV."""
    if '=' in line:
        row = dict(part.split('=', 1) for part in line.strip().split('|') if '=' in part)
        if 'size' not in row:
            return None  # e.g. a separate side-data line
        timestamp, size = row.get('dts_time' if use_dts else 'pts_time'), row['size']
        duration, flags = row.get('duration_time', '0'), row.get('flags', '')
    else:
        parts = next(csv.reader([line.strip()]))
        if len(parts) < 2:
            return None
        timestamp, size = parts[:2]
        duration, flags = 0, parts[2] if len(parts) > 2 else ''
    try:
        timestamp, size = float(timestamp), int(size)
        if not math.isfinite(timestamp) or size < 0:
            raise ValueError('Invalid timestamp or size')
    except (ValueError, TypeError, OverflowError):
        raise ValueError('Invalid timestamp or size')
    try:
        duration = float(duration)
    except (ValueError, TypeError):
        duration = 0
    if not math.isfinite(duration) or duration <= 0:
        fps = frame_rate(framerate)
        duration = 1 / fps if fps else 0
    return PacketRecord(timestamp, size, duration, 'K' in flags)


def collect_packets(process, progress_bar, task, use_dts=False, framerate=0):
    if process is None or process.stdout is None:
        raise ValueError('Invalid process object provided')
    packets, rejected = [], 0
    with io.TextIOWrapper(process.stdout, encoding='utf-8') as output:
        for line in output:
            if not line.strip():
                continue
            try:
                packet = parse_packet(line, use_dts, framerate)
            except ValueError:
                rejected += 1
                continue
            if packet is not None:
                packets.append(packet)
                progress_bar.update(task, completed=len(packets))
    code = process.wait()
    if code:
        raise RuntimeError('FFprobe failed with exit status {}. See its error output.'.format(code))
    if not packets:
        raise ValueError('No valid packets found ({} rejected). Try another stream or timestamp type.'.format(rejected))
    return sorted(packets, key=lambda packet: packet.time), rejected


class FileInfoProvider:
    def __init__(self, file_path):
        self._file_path = file_path
        self.metadata = self._probe()

    def _probe(self, stream_specifier=None):
        command = ['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json']
        if stream_specifier is not None:
            command.extend(['-select_streams', stream_specifier])
        result = subprocess.run(command + [self._file_path], stdout=subprocess.PIPE, check=True)
        return json.loads(result.stdout)

    def get_stream(self, stream_specifier=None):
        if stream_specifier is not None:
            streams = self._probe(stream_specifier).get('streams', [])
            if len(streams) != 1:
                raise ValueError('Stream specifier must select exactly one audio/video stream.')
            stream = streams[0]
        else:
            playable = [s for s in self.metadata.get('streams', []) if not s.get('disposition', {}).get('attached_pic')]
            stream = next((s for s in playable if s['codec_type'] == 'video'), None)
            stream = stream or next((s for s in playable if s['codec_type'] == 'audio'), None)
        if not stream or stream.get('codec_type') not in ('audio', 'video'):
            raise ValueError('No matching audio/video stream found.')
        return stream

    def is_video(self):
        return any(s.get('codec_type') == 'video' and not s.get('disposition', {}).get('attached_pic') for s in self.metadata.get('streams', []))

    def get_duration(self):
        value = self.metadata.get('format', {}).get('duration')
        return float(value) if value not in (None, 'N/A') else None

    def get_number_of_packets(self, stream_specifier):
        result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', stream_specifier,
                                 '-count_packets', '-show_entries', 'stream=nb_read_packets',
                                 '-of', 'json', self._file_path], stdout=subprocess.PIPE, check=True)
        return sum(int(s.get('nb_read_packets', 0)) for s in json.loads(result.stdout).get('streams', []))


class VideoInfoProvider:
    def __init__(self, video_path):
        self.info = FileInfoProvider(video_path)
        self.stream = self.info.get_stream()

    def get_video_bitrate(self):
        bitrate = self.stream.get('bit_rate')
        return '{} Mbps'.format(float(bitrate) / 1e6) if bitrate not in (None, 'N/A') else 'Not reported'

    def get_framerate_fraction(self):
        return self.stream.get('r_frame_rate', '0/0')

    def get_average_framerate(self):
        return self.stream.get('avg_frame_rate', '0/0')

    def get_framerate_number(self):
        return frame_rate(self.get_framerate_fraction())

    def is_constant_framerate(self):
        return frame_rate(self.get_framerate_fraction()) == frame_rate(self.get_average_framerate())

    def is_integer_framerate(self):
        return self.get_framerate_number().is_integer()


def line():
    print('-' * shutil.get_terminal_size(fallback=(80, 24)).columns)


def append_to_file(filename, data):
    with open(filename, 'a') as output:
        output.write(data)


def process_timestamp_and_size(parts):
    try:
        timestamp, size = float(parts[0]), int(parts[1])
        return (timestamp, size) if math.isfinite(timestamp) and size >= 0 else None
    except (ValueError, TypeError, IndexError, OverflowError):
        return None
