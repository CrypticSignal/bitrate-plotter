import math
import warnings
from utils import collect_packets


def validate_parameters(min_coverage_seconds, max_gap_seconds):
    for name, value in [('min_coverage_seconds', min_coverage_seconds), ('max_gap_seconds', max_gap_seconds)]:
        if value is not None and not 0 < value <= 1:
            raise ValueError('{} must be between 0 and 1'.format(name))


def calculate_bitrates(process, progress_bar, task_1, task_2, use_dts, output_unit,
                       min_coverage_seconds=None, max_gap_seconds=None, *,
                       framerate=0, include_partial=False):
    """Fixed one-second packet rates; complete means inside the packet timeline."""
    multipliers = {'kbps': 1e-3, 'mbps': 1e-6, 'gbps': 1e-9}
    if output_unit not in multipliers:
        raise ValueError('Invalid output unit: {}'.format(output_unit))
    validate_parameters(min_coverage_seconds, max_gap_seconds)
    if min_coverage_seconds is not None or max_gap_seconds is not None:
        warnings.warn('Packet coverage/gap thresholds are deprecated and ignored; intervals use timeline bounds.', DeprecationWarning)
    packets, rejected = collect_packets(process, progress_bar, task_1, use_dts, framerate)
    start, last = packets[0].time, packets[-1].time
    end = max(p.time + p.duration for p in packets)
    first = math.floor(start)
    stop = max(first + 1, math.floor(last) + 1, math.ceil(end - 1e-7))
    if stop - first > 2_000_000:
        raise ValueError('Timestamp range exceeds two million one-second intervals.')
    sizes, counts = {}, {}
    for i, packet in enumerate(packets, 1):
        second = math.floor(packet.time)
        sizes[second] = sizes.get(second, 0) + packet.size
        counts[second] = counts.get(second, 0) + 1
        progress_bar.update(task_2, completed=i)
    full = [s for s in range(first, stop) if s >= start - 1e-7 and s + 1 <= end + 1e-7]
    full_set = set(full)
    partial = [s for s in range(first, stop) if s not in full_set]
    seconds = list(range(first, stop)) if include_partial else full
    if not seconds:
        raise ValueError('No full one-second intervals found. Use --include-partial for short clips.')
    bitrates = [sizes.get(s, 0) * 8 * multipliers[output_unit] for s in seconds]
    packet_counts = [counts.get(s, 0) for s in seconds]
    partial_ranges = [(max(s, start), min(s + 1, end)) for s in partial]
    total_bytes = sum(p.size for p in packets)
    data = {
        'mode': 'DTS' if use_dts else 'PTS',
        'min_bitrate_' + output_unit: min(bitrates),
        'mean_bitrate_' + output_unit: sum(bitrates) / len(bitrates),
        'max_bitrate_' + output_unit: max(bitrates),
        'whole_stream_mean_bitrate_' + output_unit: total_bytes * 8 / (end - start) * multipliers[output_unit] if end > start else None,
        'complete_seconds': len(full), 'num_incomplete_seconds': len(partial),
        'included_seconds': seconds, 'include_partial': include_partial,
        'partial_timestamp_ranges': partial_ranges,
        'total_packets': len(packets), 'total_bytes': total_bytes,
        'rejected_packets': rejected,
        'timestamp_fallback_packets': sum(p.fallback for p in packets),
        'rejection_reasons': {'invalid timestamp or size': rejected} if rejected else {},
        'incomplete_reasons': {s: 'partial timeline interval' for s in partial},
        'seconds_without_packets': sum(c == 0 for c in packet_counts),
        'packets_per_second': {'min': min(packet_counts), 'max': max(packet_counts), 'avg': sum(packet_counts) / len(packet_counts)},
        'timing': {'first_timestamp': start, 'last_timestamp': last, 'end_timestamp': end, 'duration': end - start},
    }
    if partial:
        ranges = ', '.join('{:.3f}-{:.3f}s'.format(a, b) for a, b in partial_ranges)
        print('{} partial interval(s) {}: {}. Partial rates use a one-second divisor.'.format(len(partial), 'included' if include_partial else 'excluded', ranges))
        if not include_partial:
            data['unused_timestamp_range'] = ranges
    return seconds, bitrates, data
