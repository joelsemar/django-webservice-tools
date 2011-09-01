/*11111111 11100011 10001000 11000100 MP3 Header
 * 1111 1111 111 sync word  00 means mpeg2.5  01 means layer III 1 no CRC 1000 (64000 bit rate indx)
 * 10 (8000hz sample index) 0 no padding  0 non private 11 single channel 00 mode xtension 0=non copyright 1 original 00 no emphasis
 * */

#include <Python.h>
#include <structmember.h>
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

typedef struct{
    PyObject_HEAD
    AVCodec *codec;
    AVCodecContext *context;
} mp3_encoder;

static void mp3enc_dealloc(mp3_encoder* self){
	avcodec_close(self->context);
	av_free(self->context);
}

static void mp3enc_init(mp3_encoder* self, PyObject *args, PyObject *kwds){
	avcodec_init();
	avcodec_register_all();
    	
        self->codec = avcodec_find_encoder(CODEC_ID_MP3);
        if (!self->codec){
		    PyErr_SetString(PyFFmpegError, "No MP3 encoder found");
	    }

    	self->context = avcodec_alloc_context3(self->codec);

    	/* put sample parameters */
    	self->context->sample_rate = 8000;
    	self->context->channels = 1;
    	self->context->sample_fmt = AV_SAMPLE_FMT_S16;

        if (avcodec_open2(self->context, self->codec, NULL) < 0){
		    PyErr_SetString(PyFFmpegError, "Error initiliazing codec");
	}
}

static void generate_silence(char *buf, enum AVSampleFormat sample_fmt, size_t size)
	{
	int fill_char = 0x00;
	if (sample_fmt == AV_SAMPLE_FMT_U8)
		fill_char = 0x80;
	memset(buf, fill_char, size);
}


static PyObject *mp3_flush(mp3_encoder *self, PyObject *args) {

	int sample_size, outpos, osize;
        sample_size = outpos = osize = 0;

        osize = av_get_bytes_per_sample(self->context->sample_fmt);
	sample_size = self->context->frame_size * osize * self->context->channels;

    int max_data = sample_size * 5;
	char *decoded_buffer = PyMem_Malloc(max_data);
	uint8_t *decoded_data = PyMem_Malloc(max_data);
	if (decoded_buffer == NULL){
		PyErr_SetString(PyFFmpegError, "Memory not allocated - decoded_buffer");
		return NULL;
	}
	if (decoded_data == NULL){
		PyErr_SetString(PyFFmpegError, "Memory not allocated - decoded_data");
		return NULL;
	}
        int out_size = 1;      //Initial out_size to some amount to start the loop
        while(out_size > 0){
		out_size = avcodec_encode_audio(self->context, decoded_data, max_data, NULL);
        	memcpy(&decoded_buffer[outpos], decoded_data, out_size);
        	if (out_size > 0)
        		outpos += out_size;
	}

	PyObject *result = Py_BuildValue("s#", decoded_buffer, outpos);
	PyMem_Free(decoded_buffer);
	PyMem_Free(decoded_data);
	return result;
}

static PyObject *mp3_encode(mp3_encoder *self, PyObject *args) {
	char *data;
	int size, out_size, sample_size;

	if (!PyArg_ParseTuple(args, "s#", &data, &size))
		return NULL;
	
    int osize = av_get_bytes_per_sample(self->context->sample_fmt);
    sample_size = self->context->frame_size * osize * self->context->channels;


    int extra_bytes = size % sample_size;
    char *newdata;
    if (extra_bytes != 0){
        int silence_len = sample_size - extra_bytes;
        newdata = PyMem_Malloc(size+silence_len);
        memcpy(newdata, data, size);
        generate_silence(&newdata[size], self->context->sample_fmt, silence_len);
        data = newdata;
        size += silence_len;
    }
	int max_data = size*4; //calculate max_data here
	char *decoded_buffer = PyMem_Malloc(max_data);
	uint8_t *decoded_data = PyMem_Malloc(sample_size*2);
	if (decoded_buffer == NULL){
		PyErr_SetString(PyFFmpegError, "Insufficient memory");
		return NULL;
	}
	if (decoded_data == NULL){
		PyErr_SetString(PyFFmpegError, "Insufficient memory");
		return NULL;
	}

	int cur_sample = 0;
	int outpos = 0;
	while (cur_sample < size){
		out_size = avcodec_encode_audio(self->context, decoded_data, max_data, (short *) &data[cur_sample]);
		memcpy(&decoded_buffer[outpos], decoded_data, out_size);
		if (out_size > 0)
			outpos += out_size;
		cur_sample += sample_size;
	}
	PyObject *result = Py_BuildValue("s#", decoded_buffer, outpos);

	PyMem_Free(decoded_buffer);
	PyMem_Free(decoded_data);
    if (extra_bytes != 0)
        PyMem_Free(newdata);
	return result;
}

static PyMethodDef module_methods[] = {
    {NULL}
};

static PyMethodDef mp3enc_methods[] = {
		{ "mp3_encode", (PyCFunction)mp3_encode, METH_VARARGS, "Encode a chunk of PCM data into MP3 - buffer bytes to multiples of 1152 unless stream is closing" },
                { "mp3_flush", (PyCFunction)mp3_flush, METH_NOARGS, "Flush the stream"},
		{ NULL, NULL },
};

static PyTypeObject mp3_encoderType={
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "mp3_encoder",             /*tp_name*/
    sizeof(mp3_encoder),       /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)mp3enc_dealloc,/*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    0,                         /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
    "MP3 Encoder",           /* tp_doc */
    0,                         /* tp_traverse */
    0,                         /* tp_clear */
    0,                         /* tp_richcompare */
    0,                         /* tp_weaklistoffset */
    0,                         /* tp_iter */
    0,                         /* tp_iternext */
    mp3enc_methods,             /* tp_methods */
    0,                         /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    (initproc)mp3enc_init,      /* tp_init */
    0,                         /* tp_alloc */
    PyType_GenericNew,        /* tp_new */
};

#ifndef PyMODINIT_FUNC
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC initpy_ffmpeg(void) {
	PyObject *m;
        if (PyType_Ready(&mp3_encoderType) < 0)
            return;

	m = Py_InitModule3("py_ffmpeg", module_methods, "Python FFmpeg module");
	if (m == NULL)
	    return;

	PyFFmpegError = PyErr_NewException("mp3_encode.error", NULL, NULL);

	Py_INCREF(PyFFmpegError);
	PyModule_AddObject(m, "error", PyFFmpegError);

        Py_INCREF(&mp3_encoderType);
        PyModule_AddObject(m, "mp3_encoder", (PyObject *)&mp3_encoderType);
}
