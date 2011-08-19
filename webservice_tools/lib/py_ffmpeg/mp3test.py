import py_ffmpeg
pcm = open('/home/joel/whole_thing.pcm', 'rb')
out = open('/home/joel/outtest.mp3', 'wb')
data = pcm.read()
out.write(data)
"ffmpeg -ar 8000 -f s16le -i whole_thing.pcm -aq 5 output.mp3"
