import os 


def clear_current_line_in_terminal():
    width, height = os.get_terminal_size()
    print('\r' + ' ' * (width - 1) + '\r', end='')


def write_to_txt_file(filename, data, mode='a'):
    with open(filename, mode) as f:
        f.write(data)
