from argparse import ArgumentParser, RawTextHelpFormatter
from pathlib import Path
import os
import subprocess
import io
from time import time
import matplotlib.pyplot as plt

from utils import show_progress_bar, update_txt_file

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
    '-o', '--output-folder', 
    type=str, 
    help='Change the name of the folder where the data will be saved.\n'
         'If the desired folder name contains a space, it must be surrounded in double quotes.\n'
         'Default folder name: (<file being analysed>).\n'
         'i.e. if the file being analysed is video.mp4, the output folder will be named (video.mp4)\n'
         'Example: -o "my folder"'
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
output_folder = f'({filename})'
filename_without_ext = Path(args.file_path).stem

if args.output_folder:
    output_folder = args.output_folder
    
os.makedirs(output_folder, exist_ok=True)

update_txt_file(
    'This file shows the data used to create the graph. The data is in the format time --> bitrate\n'
    'At the bottom of this file, you can find the min and max bitrate from this data.\n\n',
    output_folder,
    mode='w'
)

# This command will information about file's first stream.
cmd = [
    'ffprobe', '-v', 'error', '-threads', str(os.cpu_count()), 
    '-show_streams', '-select_streams', '0', args.file_path
]

process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
first_stream = process.stdout.read().decode('utf-8').replace('\r', '').split('\n')

# Default stream specifier.
stream_specifier = 'a:0'

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
        print('It seems like you have specified an audio file. The first audio stream will be analysed.')
else:
    print(f'The bitrate of stream {args.stream_specifier} will be analysed.')

duration_cmd = [
    'ffprobe', '-v', 'error', '-threads', str(os.cpu_count()),
    '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', args.file_path
]

process = subprocess.Popen(duration_cmd, stdout=subprocess.PIPE)
duration = float(process.stdout.read().decode('utf-8'))

time_data = []
size_data = []
size_so_far = 0
get_size_so_far = False
# Get the total number of bits after 1 second. 
# After every second, this value is incremented by 1 so we can get the bitrate for the 2nd second, 3rd second, etc.
time_to_check = 1

# This command will get the necessary data from the file.
cmd = [
    'ffprobe', '-v', 'error', '-threads', str(os.cpu_count()),
    '-select_streams', stream_specifier, '-show_frames', args.file_path
]

process = subprocess.Popen(cmd, stdout=subprocess.PIPE)

start = time()

for line in io.TextIOWrapper(process.stdout, encoding="utf-8"):
    
    if 'pkt_pts_time' in line:
        timestamp = float(line[13:])

        if timestamp >= time_to_check:
            update_txt_file(f'{timestamp} --> ', output_folder)
            time_data.append(timestamp)
            eta = (time() - start) * (duration - timestamp)
            minutes = round(eta / 60)
            seconds = f'{round(eta % 60):02d}'
            show_progress_bar(timestamp, duration, extra_info=f'(ETA: {minutes}:{seconds} [M:S])')
            start = time()
            time_to_check += 1 
            get_size_so_far = True
        else:
            get_size_so_far = False

    elif 'pkt_size' in line:
        if get_size_so_far:
            update_txt_file(f'{round(size_so_far)} kbps\n', output_folder)
            size_data.append(size_so_far)
            size_so_far = 0
        else:
            size_so_far += (int(line[9:]) * 8) / 1000
            # Multiplied by 8 to convert bytes to bits, then divided by 1000 to convert to kbps

width, height = os.get_terminal_size()
print('\r' + ' ' * (width - 1) + '\r', end='')

min = round(min(size_data), 1)
max = round(max(size_data), 1)
update_txt_file(f'\nMin Bitrate: {min} kbps\nMax Bitrate: {max} kbps', output_folder)

graph_title = filename if not args.graph_title else args.graph_title

print('Creating the graph...')
plt.suptitle(graph_title)
plt.xlabel('Time (s)')
plt.ylabel('Bitrate (kbps)')
plt.plot(time_data, size_data)
plt.savefig(os.path.join(output_folder, f'{filename_without_ext}.png'))
print(f'Done! Check out the "{output_folder}" folder.')
