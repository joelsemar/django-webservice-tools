#include <Python.h>
#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "iLBC_define.h"
#include "iLBC_decode.h"

short _decode( /* (o) Number of decoded samples */
		iLBC_Dec_Inst_t *iLBCdec_inst, /* (i/o) Decoder instance */
		short *decoded_data, /* (o) Decoded signal block*/
		short *encoded_data /* (i) Encoded bytes */);

static PyObject *ILBCError;

static PyObject *decode(PyObject *self, PyObject *args) {
	short mode = 20;
	char *data;
	short decoded_datum[BLOCKL_MAX];

	if (!PyArg_ParseTuple(args, "is", &mode, &data))
		return NULL;

	iLBC_Dec_Inst_t Dec_Inst;

	initDecode(&Dec_Inst, mode, 1);

	int len = 0;
	int inpos = 0;
	int outpos = 0;
	int inlen = sizeof(data);
	short decoded_buffer[BLOCKL_MAX*(inlen % Dec_Inst.no_of_bytes)];

	while(inpos < inlen) {
		len = _decode(&Dec_Inst, decoded_datum, &data[inpos]);
		inpos += Dec_Inst.no_of_bytes;
		decoded_buffer[outpos] = decoded_datum;
		outpos += len;
	}

	return Py_BuildValue("s", *decoded_buffer);
}

static PyMethodDef methods[] = {
		{ "decode", decode, METH_VARARGS, "Decode a binary stream from ilbc to PCM" },
		{ NULL, NULL },

};

PyMODINIT_FUNC initilbc_decode(void) {
	PyObject *m;
	m = Py_InitModule("ilbc_decode", methods);
	if (m == NULL)
		return;

	ILBCError = PyErr_NewException("decode.error", NULL, NULL);
	Py_INCREF(ILBCError);
	PyModule_AddObject(m, "error", ILBCError);

}

short _decode( /* (o) Number of decoded samples */
		iLBC_Dec_Inst_t *iLBCdec_inst, /* (i/o) Decoder instance */
		short *decoded_data, /* (o) Decoded signal block*/
		short *encoded_data /* (i) Encoded bytes */
) {
	int k;
	float decblock[BLOCKL_MAX], dtmp;

	/* do actual decoding of block */

	iLBC_decode(decblock, (unsigned char *) encoded_data, iLBCdec_inst, 1);

	/* convert to short */

	for (k = 0; k < iLBCdec_inst->blockl; k++) {
		dtmp = decblock[k];

		if (dtmp < MIN_SAMPLE)
			dtmp = MIN_SAMPLE;
		else if (dtmp > MAX_SAMPLE)
			dtmp = MAX_SAMPLE;
		decoded_data[k] = (short) dtmp;
	}

	return (iLBCdec_inst->blockl);
}
