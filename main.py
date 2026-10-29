import json
from pathlib import Path
import subprocess

from args import args
from calculate_bitrates import calculate_bitrates
from calculate_gop_bitrates import calculate_gop_bitrates
from utils import FileInfoProvider, frame_rate, line

import matplotlib.pyplot as plt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn


def main():
    info = FileInfoProvider(args.file_path)
    selected = info.get_stream(args.stream_specifier)
    is_video = selected['codec_type'] == 'video'
    if args.gop and not is_video:
        raise ValueError('GOP analysis requires a video stream.')
    fps = (frame_rate(selected.get('avg_frame_rate')) or frame_rate(selected.get('r_frame_rate'))) if is_video else 0
    filename = Path(args.file_path).name
    output_dir = Path('[{}]'.format(filename))
    if args.gop:
        output_dir = output_dir / 'gop'
    output_dir.mkdir(parents=True, exist_ok=True)
    line()
    print('File: {}\nSelected stream: #{} {} ({})\nContainer duration: {}'.format(
        filename, selected['index'], selected['codec_type'], selected.get('codec_name', 'unknown'), info.get_duration()))
    if is_video:
        print('Average frame rate: {} fps (duration fallback only)'.format(fps or 'unknown'))
    line()
    use_dts = not args.pts
    # Request both timestamps so packets missing the selected one can fall back to the other.
    command = ['ffprobe', '-v', 'error', '-select_streams', str(selected['index']),
               '-show_entries', 'packet=pts_time,dts_time,duration_time,size,flags',
               '-of', 'compact=p=0:nk=0', args.file_path]
    # Inherit stderr so a probe failure cannot be mistaken for partial success.
    with subprocess.Popen(command, stdout=subprocess.PIPE) as process:
        with Progress(SpinnerColumn(), TextColumn('[progress.description]{task.description}'), BarColumn(), TaskProgressColumn()) as progress:
            task_1 = progress.add_task('Retrieving packets...', total=None)
            task_2 = progress.add_task('Calculating intervals...', total=None)
            if args.gop:
                data_file = output_dir / 'gop_statistics.txt'
                data_file.write_text('')
                ends, rates, data = calculate_gop_bitrates(process, progress, task_1, task_2, fps, data_file, use_dts)
            else:
                times, rates, data = calculate_bitrates(process, progress, task_1, task_2, use_dts,
                                                      'mbps' if is_video else 'kbps', framerate=fps,
                                                      include_partial=args.include_partial)
    data['stream'] = {'index': selected['index'], 'type': selected['codec_type'], 'codec': selected.get('codec_name')}
    plt.figure(figsize=(15, 8))
    if args.gop:
        # Each rate belongs between the GOP's start and exclusive end, not after its end.
        edges = [data['gops'][0]['start_time']] + ends
        plt.stairs(rates, edges, fill=args.graph_type == 'filled', baseline=0 if args.graph_type == 'filled' else None)
        plt.suptitle('{} - GOP bitrate'.format(filename))
        plt.xlabel('Time (s)')
        plt.ylabel('GOP bitrate (Mbps)')
        graph_name = 'GOP_bitrates_graph.png'
    else:
        unit = 'Mbps' if is_video else 'kbps'
        plt.suptitle('{}\nMin: {:.3f} | Max: {:.3f} | Chart avg: {:.3f} {}'.format(filename, min(rates), max(rates), sum(rates) / len(rates), unit))
        # Fixed buckets are steps; a joined line suggests interpolation between packets.
        plt.stairs(rates, times + [times[-1] + 1], fill=args.graph_type == 'filled', baseline=0 if args.graph_type == 'filled' else None)
        plt.xlabel('Time (s)')
        plt.ylabel('Bitrate ({})'.format(unit))
        graph_name = 'bitrates_graph.png'
    plt.grid(True, alpha=0.3)
    plt.ylim(bottom=0)
    plt.savefig(output_dir / graph_name)
    plt.close()
    with open(output_dir / 'data.json', 'w') as output:
        json.dump(data, output, indent=4)
    print("Done! Check out the '{}' folder.".format(output_dir))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, subprocess.CalledProcessError, FileNotFoundError) as error:
        raise SystemExit(str(error))
