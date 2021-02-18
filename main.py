from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import io
import os
from pathlib import Path
import subprocess

import matplotlib.pyplot as plt

from ffprobe_output_parser import parse_ffprobe_output
from utils import calc_number_of_frames, get_file_duration, write_to_txt_file

parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
parser.add_argument(
    '-f', '--file-path', 
    type=str, 
    required=True,
    help='Enter the path of the file that you want to analyse. '
         'If the path contains a space, it must be surrounded in double quotes. '
         'Example: -f "C:/Users/H/Desktop/my file.mp4"'
)
parser.add_argument(
    '-g', '--graph-type',
    #required=True,
    choices=['filled', 'unfilled'],
    default='unfilled',
    help='Specify the type of graph that should be created. '
         'To see the difference between a filled and unfilled graph, check out the example graph files.'
)
parser.add_argument(
    '-se', '--show-entries', 
    type=str,
    default='packet=pts_time,size',
    help='Use FFprobe\'s -show_entries option to specify what to output. Example: -se frame=key_frame,pkt_pts_time'
)
parser.add_argument(
    '-ngm', '--no-graph-mode', 
    action='store_true',
    help='Enable "no graph mode" which simply writes the output of ffprobe to a .txt file. '
         'You should also use the --show-entries argument to specify what information you want ffprobe to output.'
)
parser.add_argument(
    '-s', '--stream-specifier', 
    type=str, 
    help='Use FFmpeg stream specifier syntax to specify the audio/video stream that you want to analyse. '
         'The defaults for audio and video files are a:0 and V:0, respectively. '
         'Stream index starts at 0, therefore, as an example, to target the 2nd audio stream, enter -s a:1'
)

args = parser.parse_args()
filename = Path(args.file_path).name
filename_without_ext = Path(args.file_path).stem
# The bitrate every second will be saved to this file in the format timestamp --> bitrate 
# This is so users can see the specific values that were used to plot the graph
# The bitrates in this file are rounded to the nearest integer.
timestamp_bitrate_file = f'{filename_without_ext}.txt'

# This command will information about file's first stream.
cmd = [
    'ffprobe', '-v', 'error', '-threads', str(os.cpu_count()), 
    '-show_streams', '-select_streams', '0', args.file_path
]

process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
first_stream = process.stdout.read().decode('utf-8').replace('\r', '').split('\n')

if not args.stream_specifier:
    if 'codec_type=video' in first_stream:
        print('Video file detected. The video stream will be analysed.')
        stream_specifier = 'V:0'
    elif 'codec_type=subtitle' in first_stream:
        print(
            'It seems like you have specified a video file. The video stream will be analysed.\n'
            'If this is not what you want, re-run this program using the -s argument '
            'to manually specify the stream to analyse.'
        )
        stream_specifier = 'V:0'
    else:
        stream_specifier = 'a:0'
        print('It seems like you have specified an audio file. The first audio stream will be analysed.')
else:
    stream_specifier = args.stream_specifier
    print(f'The bitrate of stream {args.stream_specifier} will be analysed.')

file_duration = get_file_duration(args.file_path, stream_specifier)

if 'V' in stream_specifier or 'v' in stream_specifier:
    number_of_frames = calc_number_of_frames(args.file_path, stream_specifier, file_duration)

# To calculate the bitrate every second, FFprobe needs to output the following entries.
entries = 'packet=pts_time,size'

if args.no_graph_mode:
    entries = args.show_entries

# The FFprobe command that will output the timestamps and packet sizes in CSV format.
cmd = [
    'ffprobe', '-v', 'error', '-threads', str(os.cpu_count()),
    '-select_streams', stream_specifier, 
    '-show_entries', entries, '-of', 'csv',
    args.file_path
]
process = subprocess.Popen(cmd, stdout=subprocess.PIPE)

if args.no_graph_mode:
    ffprobe_output_path = f'{filename} (FFprobe Data)/{entries}.txt'
    os.makedirs(f'{filename} (FFprobe Data)', exist_ok=True)
    frame_count = 0
    gop_length = 0
    print('-----------------------------------------------------------------------------------------------------------')
    print(f'{args.show_entries} data is being written to /{ffprobe_output_path}...')

    if 'key_frame' in args.show_entries or 'pict_type' in args.show_entries:
        for line in io.TextIOWrapper(process.stdout):
            frame_count += 1
            percentage_progress = round((frame_count / number_of_frames) * 100, 1)
            print(f'Progress: {percentage_progress}%', end='\r')
            gop_length += 1
            # When splitting the CSV output, if one o 
            if '1' in line.strip().split(',') or 'I' in line.strip().split(',') or \
               'Iside_data' in line.strip().split(','):
                print('-----------------------------------------------------------------------------------------------')
                print(f'Frame {frame_count} is a keyframe/I-frame')
                if gop_length != 1:
                    print(f'GOP length was {gop_length} frames')  
                # We have reached the next keyframe, set gop_length to 0 to calculate the next GOP length.
                gop_length = 0 
    else:
        for line in io.TextIOWrapper(process.stdout, encoding="utf-8"):
            write_to_txt_file(ffprobe_output_path, line)
    print(f'Done! Check out the following path: /{ffprobe_output_path}')

else:
    with open(timestamp_bitrate_file, 'w'): pass
    # Parse the ffprobe output save the timestamps and bitrates in lists named time_data and size_data, respectively.
    time_data, size_data = parse_ffprobe_output(process, timestamp_bitrate_file, file_duration)

    min = round(min(size_data), 1)
    max = round(max(size_data), 1)
    write_to_txt_file(timestamp_bitrate_file, f'\nMin Bitrate: {min} kbps\nMax Bitrate: {max} kbps')

    print('Creating the graph...')
    plt.suptitle(filename)
    plt.xlabel('Time (s)')
    plt.ylabel('Bitrate (kbps)')
    if args.graph_type == 'filled':
        plt.fill_between(time_data, size_data)
    plt.plot(time_data, size_data)
    print('Done! The graph will open in a new window.')
    plt.show()
