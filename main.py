from argparse import ArgumentParser, RawTextHelpFormatter
from pathlib import Path
import os
import subprocess
import io
from time import time
import matplotlib.pyplot as plt

from ffprobe_output_parser import parse_ffprobe_output
from utils import write_to_txt_file

parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
parser.add_argument(
    '-f', '--file-path', 
    type=str, 
    required=True,
    help='Enter the path of the file that you want to analyse.\n'
         'If the path contains a space, it must be surrounded in double quotes.\n'
         'Example: -f "C:/Users/H/Desktop/my file.mp4"'
)
parser.add_argument(
    '-g', '--graph-type',
    required=True,
    choices=['filled', 'unfilled'],
    help='Specify the type of graph that should be created.\n'
         'To see the difference between a filled and unfilled graph, check out the example graph files.'
)
parser.add_argument(
    '-s', '--stream-specifier', 
    type=str, 
    help='Use FFmpeg stream specifier syntax to specify the audio/video stream that you want to analyse.\n'
         'The defaults for audio and video files are a:0 and V:0, respectively.\n'
         'Stream index starts at 0, therefore, as an example, to target the 2nd audio stream, enter -s a:1'
)
parser.add_argument(
    '-t', '--graph-title', 
    type=str,
    help='Specify a title for the output graph.\n'
         'By default, the title of the graph will simply be the name of the file that was analysed.'
)

args = parser.parse_args()
filename = Path(args.file_path).name
filename_without_ext = Path(args.file_path).stem

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

duration_cmd = [
    'ffprobe', '-v', 'error', '-threads', str(os.cpu_count()), '-select_streams', stream_specifier,
    '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', args.file_path
]

process = subprocess.Popen(duration_cmd, stdout=subprocess.PIPE)
file_duration = float(process.stdout.read().decode('utf-8'))

# We need to get the values of pkt_pts_time and pkt_size
entries = 'frame=pkt_pts_time,pkt_size'

# This command will get the necessary data from the file.
cmd = [
    'ffprobe', '-v', 'error', '-threads', str(os.cpu_count()),
    '-select_streams', stream_specifier, '-show_entries', entries,
    '-of', 'default=noprint_wrappers=1',
    args.file_path
]
process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
time_data, size_data = parse_ffprobe_output(process, filename_without_ext, file_duration)

# Clear the progress and ETA information.
width, height = os.get_terminal_size()
print('\r' + ' ' * (width - 1) + '\r', end='')

min = round(min(size_data), 1)
max = round(max(size_data), 1)
write_to_txt_file(filename_without_ext, f'\nMin Bitrate: {min} kbps\nMax Bitrate: {max} kbps')

graph_title = filename if not args.graph_title else args.graph_title
print('Creating the graph...')
plt.suptitle(graph_title)
plt.xlabel('Time (s)')
plt.ylabel('Bitrate (kbps)')
if args.graph_type == 'filled':
    plt.fill_between(time_data, size_data)
plt.plot(time_data, size_data)
print('Done! The graph will open in a new window.')
plt.show()
