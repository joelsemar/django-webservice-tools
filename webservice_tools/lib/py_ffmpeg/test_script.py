import py_ffmpeg

fin = open('wholething.pcm', 'rb')

data = fin.read()

fin.close()

encoded = py_ffmpeg.mp3_encode(data)

fout = open('wholething.mp3', 'wb')

fout.write(encoded)

fout.close
