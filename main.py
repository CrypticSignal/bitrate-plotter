from argparse import ArgumentParser, RawTextHelpFormatter
from pathlib import Path
import os
import subprocess
import matplotlib.pyplot as plt

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
    default='a:0',
    help='Use FFmpeg stream specifier syntax to specify the audio/video stream that you want to analyse.\n'
         'By default, the graph is based on the first audio stream.\n'
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


def update_txt_file(text, mode='a'):
    with open(f'{output_folder}/Raw Data.txt', mode) as f:
        f.write(text)


update_txt_file(
    'This file shows the data used to create the graph. The data is in the format time --> bitrate\n'
    'At the bottom of this file, you can find the min and max bitrate from this data.\n\n', 
    mode='w'
)

process = subprocess.Popen(
    'ffprobe -loglevel warning'
    f' -select_streams {args.stream_specifier} -show_frames {args.file_path}', 
    stdout=subprocess.PIPE
)

output = process.stdout.read().decode('utf-8').split('\n')

# Get the total number of bits after 1 second. 
# After every second, this value is incremented by 1 so we can get the bitrate for the 2nd second, 3rd second, etc.
time_to_check = 1

time_data = []
size_data = []
size_so_far = 0
get_size_so_far = False

for line in output:

    if 'pkt_pts_time' in line:
        time = float(line[13:])

        if time >= time_to_check:
            update_txt_file(f'{time} --> ')
            time_data.append(time)
            time_to_check += 1 
            get_size_so_far = True
        else:
            get_size_so_far = False

    elif 'pkt_size' in line:
        if get_size_so_far:
            update_txt_file(f'{round(size_so_far)} kbps\n')
            size_data.append(size_so_far)
            size_so_far = 0
        else:
            size_so_far += (int(line[9:]) * 8) / 1000
            # Multiplied by 8 to convert bytes to bits, then divided by 1000 to convert to kbps

min = round(min(size_data), 1)
max = round(max(size_data), 1)
update_txt_file(f'\nMin Bitrate: {min} kbps\nMax Bitrate: {max} kbps')

graph_title = filename if not args.graph_title else args.graph_title

print('Creating the graph...')
plt.suptitle(graph_title)
plt.xlabel('Time (s)')
plt.ylabel('Bitrate (kbps)')
plt.plot(time_data, size_data)
plt.savefig(os.path.join(output_folder, f'{filename_without_ext}.png'))
print(f'Done! Check out the "{output_folder}" folder.')
