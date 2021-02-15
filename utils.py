import os
import sys


def show_progress_bar(progress, total, dp=1, extra_info=''):
    width, height = os.get_terminal_size()
    extra_info_len = len(extra_info)
    bar_length = width - extra_info_len - 10
    filled_length = int(bar_length * (progress / total))

    bar = ('█' * filled_length) + ('-' * (bar_length - filled_length))
    percentage_complete = round(100.0 * (progress / total), dp)

    sys.stdout.write(f'|{bar}| {percentage_complete}% {extra_info}\r')
    sys.stdout.flush() 


def update_txt_file(text, output_folder, mode='a'):
    with open(f'{output_folder}/Raw Data.txt', mode) as f:
        f.write(text)
