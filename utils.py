def write_to_txt_file(filename_without_ext, data, mode='a'):
    with open(f'{filename_without_ext}.txt', mode) as f:
        f.write(data)
