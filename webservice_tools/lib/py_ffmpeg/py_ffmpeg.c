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

static PyObject *mp3_encode(PyObject *self, PyObject *args) {
	avcodec_init();
	avcodec_register_all();

	char *data;
	AVCodecContext *c= NULL;
	int size, framesize;
	int out_size, sample_size;

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
    	printf("%s", "No codec init\n");
    	return Py_BuildValue("s", "No codec init");
    }

	if (!PyArg_ParseTuple(args, "s#", &data, &size)){
		printf("%s", "No data in\n");
		return Py_BuildValue("s", "No Data In");
	}

	framesize = c->frame_size;
	sample_size = framesize * 2 * c->channels;
	int max_data = size*2; //calculate max_data here
	char *decoded_buffer = PyMem_Malloc(max_data);
	uint8_t *decoded_data = PyMem_Malloc(sample_size*2);

	int cur_sample = 0;
	int outpos = 0;
	while (cur_sample < size){
		out_size = avcodec_encode_audio(c, decoded_data, max_data, (short *) &data[cur_sample]);
		memcpy(&decoded_buffer[outpos], decoded_data, out_size);
		outpos += out_size;
		cur_sample += sample_size;
	}

	PyObject *result = Py_BuildValue("s#", decoded_buffer, outpos);
	PyMem_Free(decoded_buffer);  //Free the memory
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

