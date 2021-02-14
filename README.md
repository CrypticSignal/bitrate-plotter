# Bitrate Variation Plotter
A command line program that plots a graph showing the variation of the bitrate throughout the specified audio/video file.

You can find an example graph below:

![Example Graph](https://github.com/CrypticSignal/bitrate-variation-plotter/blob/main/Example%20Graph.png)

*The above graph is for a Variable Bitrate (VBR) MP3 file, encoded using the -V0 setting of the [LAME](https://lame.sourceforge.io/) encoder.*

In addition to this, the data used to plot the graph is saved in a file named `Raw Data.txt`. The data is in the format `timestamp --> bitrate`. Here is a sample:
```
1.008 --> 223 kbps
2.016 --> 257 kbps
3.0 --> 239 kbps
4.008 --> 250 kbps
5.016 --> 263 kbps
6.0 --> 253 kbps
7.008 --> 264 kbps
8.016 --> 267 kbps
9.0 --> 260 kbps
10.008 --> 266 kbps
```

# Requirements 
- Python 3.6+
- FFprobe executable in your PATH.

# Usage
Using this program is very simple. As an example, to analyse the video bitrate of a file named video.mp4 in the current directory, enter `python main.py -f video.mp4 -s v:0`. To analyse the bitrate of the first audio stream, the `-s` argument is not required and you can simply enter `python main.py -f video.mp4`.

The only argument that is required is the path of the file that you wish to analyse. All other arguments are optional. You can find the output of `python main.py -h` below:
```
usage: main.py [-h] -f FILE_PATH [-o OUTPUT_FOLDER] [-s STREAM_SPECIFIER] [-t GRAPH_TITLE]

optional arguments:
  -h, --help            show this help message and exit
  -f FILE_PATH, --file-path FILE_PATH
                        Enter the path of the file that you want to analyse.
                        If the path contains a space, it must be surrounded in double quotes.
                        Example: -f "C:/Users/H/Desktop/my file.mp4"
  -o OUTPUT_FOLDER, --output-folder OUTPUT_FOLDER
                        Change the name of the folder where the data will be saved.
                        If the desired folder name contains a space, it must be surrounded in double quotes.
                        Default folder name: (<file being analysed>).
                        i.e. if the file being analysed is video.mp4, the output folder will be named (video.mp4)
                        Example: -o "my folder"
  -s STREAM_SPECIFIER, --stream-specifier STREAM_SPECIFIER
                        Use FFmpeg stream specifier syntax to specify the audio/video stream that you want to analyse.
                        By default, the graph is based on the first audio stream.
                        Stream index starts at 0, therefore, as an example, to target the 2nd audio stream, enter -s a:1
  -t GRAPH_TITLE, --graph-title GRAPH_TITLE
                        Specify a title for the output graph.
                        By default, the title of the graph will simply be the name of the file that was analysed.
```