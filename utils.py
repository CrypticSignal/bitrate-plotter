def update_txt_file(text, output_folder, mode='a'):
    with open(f'{output_folder}/Raw Data.txt', mode) as f:
        f.write(text)
