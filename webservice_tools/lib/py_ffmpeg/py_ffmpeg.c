/*11111111 11100011 10001000 11000100 MP3 Header
 * 1111 1111 111 sync word  00 means mpeg2.5  01 means layer III 1 no CRC 1000 (64000 bit rate indx)
 * 10 (8000hz sample index) 0 no padding  0 non private 11 single channel 00 mode xtension 0=non copyright 1 original 00 no emphasis
 * */

#include <Python.h>
#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#ifdef HAVE_AV_CONFIG_H
#undef HAVE_AV_CONFIG_H
#endif

#include <libavcodec/avcodec.h>
#include <libavutil/mathematics.h>

static PyObject *PyFFmpegError;

static void generate_silence(uint8_t* buf, enum AVSampleFormat sample_fmt, size_t size)
	{
	int fill_char = 0x00;
	if (sample_fmt == AV_SAMPLE_FMT_U8)
		fill_char = 0x80;
	memset(buf, fill_char, size);
}

static PyObject *mp3_encode(PyObject *self, PyObject *args) {
	avcodec_init();
	avcodec_register_all();

	char *data;
	AVCodecContext *c= NULL;
	int size, out_size, sample_size;

	AVCodec *codec;

    	codec = avcodec_find_encoder(CODEC_ID_MP3);
    	if (!codec) {
    		printf("%s", "No encoder\n");
    		return Py_BuildValue("s", "No encoder");
    	}

    	c = avcodec_alloc_context3(codec);

    	/* put sample parameters */
    	c->sample_rate = 8000;
    	c->channels = 1;
    	c->sample_fmt = AV_SAMPLE_FMT_S16;

    	if (avcodec_open2(c, codec, NULL) < 0) {
    		return Py_BuildValue("s", "No codec init");
	}

	if (!PyArg_ParseTuple(args, "s#", &data, &size))
		return NULL;


	int osize = av_get_bytes_per_sample(c->sample_fmt);
	sample_size = c->frame_size * osize * c->channels;


        int extra_bytes = size % sample_size;
        char *newdata;
        if (extra_bytes != 0){
        	int silence_len = sample_size - extra_bytes;
		newdata = PyMem_Malloc(size+silence_len);
		memcpy(newdata, data, size);
		generate_silence(&newdata[size], c->sample_fmt, silence_len);
		data = newdata;
		size += silence_len;
        }
	int max_data = size*4; //calculate max_data here
	char *decoded_buffer = PyMem_Malloc(max_data);
	uint8_t *decoded_data = PyMem_Malloc(sample_size*2);
	if (decoded_buffer == NULL){
		PyErr_SetString(PyFFmpegError, "Memory not allocated - decoded_buffer");
		return NULL;
	}
	if (decoded_data == NULL){
		PyErr_SetString(PyFFmpegError, "Memory not allocated - decoded_data");
		return NULL;
	}

	int cur_sample = 0;
	int outpos = 0;
	while (cur_sample < size){
		out_size = avcodec_encode_audio(c, decoded_data, max_data, (short *) &data[cur_sample]);
		memcpy(&decoded_buffer[outpos], decoded_data, out_size);
		if (out_size > 0)
			outpos += out_size;
		cur_sample += sample_size;
	}
        while(out_size > 0){
		out_size = avcodec_encode_audio(c, decoded_data, max_data, NULL);
        	memcpy(&decoded_buffer[outpos], decoded_data, out_size);
        	if (out_size > 0)
        		outpos += out_size;
	}
	PyObject *result = Py_BuildValue("s#", decoded_buffer, outpos);

	PyMem_Free(decoded_buffer);
	PyMem_Free(decoded_data);

	avcodec_close(c);
	av_free(c);

	return result;
}

static PyMethodDef methods[] = {
		{ "mp3_encode", mp3_encode, METH_VARARGS, "" },
		{ NULL, NULL },

};

PyMODINIT_FUNC initpy_ffmpeg(void) {
	PyObject *m;
	m = Py_InitModule("py_ffmpeg", methods);
	if (m == NULL)
		return;

	PyFFmpegError = PyErr_NewException("mp3_encode.error", NULL, NULL);
	Py_INCREF(PyFFmpegError);
	PyModule_AddObject(m, "error", PyFFmpegError);

}
