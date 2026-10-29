import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from calculate_bitrates import calculate_bitrates
from calculate_gop_bitrates import calculate_gop_bitrates, GOP, Packet, VideoStats
from utils import frame_rate, parse_packet, process_timestamp_and_size


class Progress:
    def update(self, *args, **kwargs):
        pass


class Process:
    def __init__(self, rows, code=0):
        self.stdout = io.BytesIO(('\n'.join(rows) + '\n').encode())
        self.code = code

    def wait(self):
        return self.code


def row(time, size=1000, duration=None, key=False, basis='pts'):
    return '{}_time={}|duration_time={}|size={}|flags={}'.format(basis, time, 'N/A' if duration is None else duration, size, 'K__' if key else '___')


def seconds(rows, **kwargs):
    return calculate_bitrates(Process(rows), Progress(), 0, 1, kwargs.pop('use_dts', False), kwargs.pop('output_unit', 'mbps'), **kwargs)


class SecondsTests(unittest.TestCase):
    def test_exact_three_seconds_include_final_full_interval(self):
        times, rates, data = seconds([row(i / 25, duration=.04) for i in range(75)])
        self.assertEqual(times, [0, 1, 2])
        for rate in rates:
            self.assertAlmostEqual(rate, .2)
        self.assertEqual(data['num_incomplete_seconds'], 0)

    def test_negative_times_use_floor_and_report_real_exclusions(self):
        times, rates, data = seconds([row(-.04, 100, .04), row(0, 1000, 1), row(1, 200, .25)])
        self.assertEqual(times, [0])
        self.assertAlmostEqual(rates[0], .008)
        self.assertEqual(data['partial_timestamp_ranges'], [(-.04, 0), (1, 1.25)])
        self.assertEqual(data['total_bytes'], 1300)

    def test_sparse_and_low_rate_streams_keep_full_zero_buckets(self):
        times, rates, data = seconds([row(10, 125000, 1), row(12, 250000, 1)])
        self.assertEqual(times, [10, 11, 12])
        self.assertEqual(rates, [1, 0, 2])
        self.assertEqual(data['seconds_without_packets'], 1)
        self.assertEqual(data['mean_bitrate_mbps'], 1)
        self.assertEqual(seconds([row(0, 100, .5), row(.5, 200, .5)])[0], [0])

    def test_fractional_edges_and_optional_partial_divisor(self):
        rows = [row(.2, 125000, .2), row(2.2, 250000, .2)]
        self.assertEqual(seconds(rows)[0], [1])
        times, rates, data = seconds(rows, include_partial=True)
        self.assertEqual(times, [0, 1, 2])
        # 1 Mbit over 0.2-1.0s and 2 Mbit over 2.0-2.4s.
        for rate, expected in zip(rates, [1.25, 0, 5]):
            self.assertAlmostEqual(rate, expected)
        self.assertEqual(data['summary_seconds'], [1])
        for edge, expected in zip(data['interval_edges'], [.2, 1, 2, 2.4]):
            self.assertAlmostEqual(edge, expected)
        self.assertEqual((data['min_bitrate_mbps'], data['max_bitrate_mbps'], data['mean_bitrate_mbps']), (0, 0, 0))
        self.assertAlmostEqual(data['whole_stream_mean_bitrate_mbps'], 3 / 2.2)

    def test_short_unknown_and_excessive_timelines(self):
        with self.assertRaisesRegex(ValueError, 'include-partial'):
            seconds([row(0, 100)])
        with self.assertRaisesRegex(ValueError, 'measurable duration'):
            seconds([row(0, 100)], include_partial=True)
        times, rates, data = seconds([row(0, 100), row(1, 100)], include_partial=True)
        self.assertEqual(times, [0])
        self.assertAlmostEqual(rates[0], .0008)
        self.assertEqual(seconds([row(0), row(1)])[0], [0])
        with self.assertRaisesRegex(ValueError, 'two million'):
            seconds([row(0), row(3000000)])

    def test_units_fallback_and_invalid_records(self):
        for unit, expected in [('kbps', 1000), ('mbps', 1), ('gbps', .001)]:
            self.assertAlmostEqual(seconds([row(0, 125000, 1)], output_unit=unit)[1][0], expected)
        _, rates, data = seconds([row('NaN'), row('inf'), row(0, -1), row(0, 1000)], framerate=1)
        self.assertEqual(data['rejected_packets'], 3)
        self.assertAlmostEqual(rates[0], .008)
        self.assertIsNone(process_timestamp_and_size(['nan', '100']))
        self.assertEqual(frame_rate('30000/1001'), 30000 / 1001)
        self.assertEqual(frame_rate('0/0'), 0)
        self.assertEqual(parse_packet('side_data_type=Skip Samples'), None)

    def test_missing_timestamp_falls_back_to_other_basis(self):
        both = 'pts_time={}|dts_time={}|duration_time=1|size=125000|flags=K__'
        _, rates, data = seconds([both.format(0, 'N/A'), both.format(1, 1)], use_dts=True)
        self.assertEqual(rates, [1, 1])
        self.assertEqual(data['timestamp_fallback_packets'], 1)
        self.assertEqual(data['rejected_packets'], 0)
        self.assertTrue(parse_packet(both.format('N/A', 2), use_dts=False).fallback)
        self.assertFalse(parse_packet(both.format(5, 2)).fallback)
        self.assertEqual(parse_packet(both.format(5, 2)).time, 2)
        with self.assertRaises(ValueError):
            parse_packet(both.format('N/A', 'N/A'))

    def test_probe_failure_never_reports_partial_success(self):
        with self.assertRaisesRegex(RuntimeError, 'exit status 1'):
            calculate_bitrates(Process([row(0, duration=1)], code=1), Progress(), 0, 1, False, 'mbps')


class GOPTests(unittest.TestCase):
    def calculate(self, rows, framerate=0):
        with tempfile.TemporaryDirectory() as directory:
            return calculate_gop_bitrates(Process(rows), Progress(), 0, 1, framerate, str(Path(directory) / 'stats.txt'), False)

    def test_variable_boundaries_and_final_durations(self):
        ends, rates, data = self.calculate([row(0, 100, .1, True), row(.1, 200, .2), row(.3, 300, .1, True), row(.4, 400, .3)])
        self.assertEqual(len(rates), 2)
        self.assertAlmostEqual(ends[0], .3)
        self.assertAlmostEqual(ends[1], .7)
        self.assertAlmostEqual(rates[0], .008)
        self.assertAlmostEqual(rates[1], .014)
        self.assertAlmostEqual(data['gops'][1]['duration'], .4)

    def test_weighted_average_excludes_pre_keyframe_packets(self):
        packets = [Packet(-1, 50, ''), Packet(0, 1, 'K', 1), Packet(1, 1, 'K', 3)]
        stats = VideoStats(packets, [GOP(0, [packets[1]]), GOP(1, [packets[2]])], 0)
        self.assertAlmostEqual(stats.get_gop_stats_range()['bitrate'][2], .5)
        self.assertEqual(stats.gop_stats[0].duration, 1)
        self.assertEqual(stats.gop_stats[1].duration, 3)

    def test_latest_packet_end_and_fractional_frame_rate_fallback(self):
        ends, rates, _ = self.calculate([row(0, 100, 2, True), row(1, 100, .25)])
        self.assertEqual(ends, [2])
        self.assertAlmostEqual(rates[0], .0008)
        ends, rates, _ = self.calculate([row(0, 100, None, True)], '25/1')
        self.assertAlmostEqual(ends[0], .04)
        self.assertAlmostEqual(rates[0], .02)

    def test_no_keyframes_unknown_duration_and_probe_errors_are_actionable(self):
        for rows in [[row(0, duration=1)], [row(0, key=True)]]:
            with self.assertRaises(RuntimeError):
                self.calculate(rows)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Native FFmpeg required')
class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temp.name) / 'bframes.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=160x90:rate=25',
                        '-f', 'lavfi', '-i', 'sine=sample_rate=48000', '-t', '3.2', '-c:v', 'libx264',
                        '-bf', '2', '-g', '25', '-c:a', 'aac', str(cls.path)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def probe(self, basis, spec='v:0', path=None):
        data = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', spec, '-show_packets', '-of', 'json', str(path or self.path)]))
        rows = [p for p in data['packets'] if basis in p]
        return rows

    def process(self, basis, spec='v:0', path=None):
        return subprocess.Popen(['ffprobe', '-v', 'error', '-select_streams', spec,
                                 '-show_entries', 'packet={},duration_time,size,flags'.format(basis),
                                 '-of', 'compact=p=0:nk=0', str(path or self.path)], stdout=subprocess.PIPE)

    def test_pts_dts_audio_and_video_match_independent_native_packet_sums(self):
        for spec in ['v:0', 'a:0']:
            for basis in ['pts_time', 'dts_time']:
                with self.subTest(spec=spec, basis=basis):
                    rows = self.probe(basis, spec)
                    start = min(float(p[basis]) for p in rows)
                    end = max(float(p[basis]) + float(p.get('duration_time', 0)) for p in rows)
                    expected_times = [s for s in range(math.floor(start), math.ceil(end)) if s >= start - 1e-7 and s + 1 <= end + 1e-7]
                    with self.process(basis, spec) as process:
                        times, rates, data = calculate_bitrates(process, Progress(), 0, 1, basis == 'dts_time', 'mbps')
                    self.assertEqual(times, expected_times)
                    for second, rate in zip(times, rates):
                        expected_bytes = sum(int(p['size']) for p in rows if second <= float(p[basis]) < second + 1)
                        self.assertAlmostEqual(rate, expected_bytes * 8 / 1e6)
                    self.assertEqual(data['total_bytes'], sum(int(p['size']) for p in rows))

    def test_gop_rates_match_independent_native_groups(self):
        for basis in ['pts_time', 'dts_time']:
            with self.subTest(basis=basis):
                groups = []
                for packet in sorted(self.probe(basis), key=lambda p: float(p[basis])):
                    if 'K' in packet['flags']:
                        groups.append([])
                    if groups:
                        groups[-1].append(packet)
                with self.process(basis) as process:
                    ends, rates, data = calculate_gop_bitrates(process, Progress(), 0, 1, 25, str(Path(self.temp.name) / 'stats.txt'), basis == 'dts_time')
                self.assertEqual(len(rates), len(groups))
                for i, group in enumerate(groups):
                    end = float(groups[i + 1][0][basis]) if i + 1 < len(groups) else max(float(p[basis]) + float(p['duration_time']) for p in group)
                    self.assertAlmostEqual(ends[i], end)
                    duration = end - float(group[0][basis])
                    self.assertAlmostEqual(rates[i], sum(int(p['size']) for p in group) * 8 / 1e6 / duration)

    def test_variable_frame_rate_cli_uses_packet_durations(self):
        path = Path(self.temp.name) / 'variable.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=160x90:rate=25',
                        '-vf', "select='not(mod(n,3))+not(mod(n,5))'", '-fps_mode', 'vfr', '-t', '3.2', '-c:v', 'libx264', '-bf', '0', '-g', '10', str(path)], check=True)
        rows = self.probe('pts_time', path=path)
        self.assertGreater(len({p['duration_time'] for p in rows}), 1)
        main = str(Path(__file__).resolve().parents[1] / 'main.py')
        result = subprocess.run([sys.executable, main, '-f', str(path), '-gop'], cwd=self.temp.name,
                                env=dict(os.environ, MPLBACKEND='Agg'), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((Path(self.temp.name) / '[variable.mp4]' / 'gop' / 'data.json').read_text())
        final_end = max(float(p['pts_time']) + float(p['duration_time']) for p in rows)
        self.assertAlmostEqual(data['gops'][-1]['end_time'], final_end)
        total_bits = sum(g['size_megabits'] for g in data['gops'])
        total_duration = sum(g['duration'] for g in data['gops'])
        self.assertAlmostEqual(float(data['gop_bitrate_range_mbps']['mean']), total_bits / total_duration, places=2)

    def test_nonzero_mpegts_timeline_and_short_audio_cli(self):
        path = Path(self.temp.name) / 'offset.ts'
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(self.path), '-c', 'copy', '-f', 'mpegts', str(path)], check=True)
        rows = self.probe('dts_time', path=path)
        with self.process('dts_time', path=path) as process:
            times, rates, data = calculate_bitrates(process, Progress(), 0, 1, True, 'mbps')
        self.assertGreater(data['timing']['first_timestamp'], 1)
        for second, rate in zip(times, rates):
            self.assertAlmostEqual(rate, sum(int(p['size']) for p in rows if second <= float(p['dts_time']) < second + 1) * 8 / 1e6)
        short = Path(self.temp.name) / 'short.wav'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=sample_rate=48000', '-t', '0.2', '-c:a', 'pcm_s16le', str(short)], check=True)
        main = str(Path(__file__).resolve().parents[1] / 'main.py')
        command = [sys.executable, main, '-f', str(short)]
        kwargs = dict(cwd=self.temp.name, env=dict(os.environ, MPLBACKEND='Agg'), capture_output=True, text=True)
        self.assertNotEqual(subprocess.run(command, **kwargs).returncode, 0)
        result = subprocess.run(command + ['--include-partial'], **kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((Path(self.temp.name) / '[short.wav]' / 'data.json').read_text())
        self.assertEqual(data['total_bytes'], 19200)
        self.assertAlmostEqual(data['mean_bitrate_kbps'], 768)
        self.assertAlmostEqual(data['whole_stream_mean_bitrate_kbps'], 768)

    def test_cli_defaults_to_dts_and_keeps_matroska_packets_without_dts(self):
        path = Path(self.temp.name) / 'bframes.mkv'
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(self.path), '-map', '0:v', '-c', 'copy', str(path)], check=True)
        rows = self.probe('size', path=path)
        missing = sum(p.get('dts_time', 'N/A') == 'N/A' for p in rows)
        self.assertGreater(missing, 0)
        main = str(Path(__file__).resolve().parents[1] / 'main.py')
        result = subprocess.run([sys.executable, main, '-f', str(path)], cwd=self.temp.name,
                                env=dict(os.environ, MPLBACKEND='Agg'), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((Path(self.temp.name) / '[bframes.mkv]' / 'data.json').read_text())
        self.assertEqual(data['mode'], 'DTS')
        self.assertEqual(data['timestamp_fallback_packets'], missing)
        self.assertEqual(data['total_bytes'], sum(int(p['size']) for p in rows))

    def test_cli_audio_selection_gop_and_short_clip(self):
        main = str(Path(__file__).resolve().parents[1] / 'main.py')
        commands = [[], ['-dts'], ['-pts'], ['-s', 'a:0'], ['-gop'], ['-gop', '-pts'], ['-s', 'v:0', '-gop', '-g', 'filled']]
        env = dict(os.environ, MPLBACKEND='Agg')
        for options in commands:
            with self.subTest(options=options):
                result = subprocess.run([sys.executable, main, '-f', str(self.path)] + options, cwd=self.temp.name, env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                directory = Path(self.temp.name) / '[bframes.mp4]'
                if '-gop' in options:
                    directory /= 'gop'
                data = json.loads((directory / 'data.json').read_text())
                self.assertTrue(list(directory.glob('*.png')))
                self.assertEqual(data['mode'], 'PTS' if '-pts' in options else 'DTS')
                if options == ['-s', 'a:0']:
                    self.assertEqual(data['stream']['type'], 'audio')
                    self.assertIn('mean_bitrate_kbps', data)
        for options, message in [(['-s', 'a:0', '-gop'], 'requires a video'), (['-s', 'a:99'], 'exactly one')]:
            result = subprocess.run([sys.executable, main, '-f', str(self.path)] + options, cwd=self.temp.name, env=env, capture_output=True, text=True)
            if message:
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)


if __name__ == '__main__':
    unittest.main()
