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
	const int size;
	short decoded_data[BLOCKL_MAX];

	if (!PyArg_ParseTuple(args, "is#", &mode, &data, &size))
		return NULL;

	iLBC_Dec_Inst_t Dec_Inst;

	initDecode(&Dec_Inst, mode, 1);

	int len = 0;
	int inpos = 0;
	int outpos = 0;
	int count = 0; //temp variable for writing the buffer to file
	int max_data = BLOCKL_MAX*size/Dec_Inst.no_of_bytes*2;
	int arrayCopyNdx = 0;
	char *decoded_buffer = malloc(max_data);
	FILE *outcfile;
	outcfile = fopen("whole_c_out.pcm", "wb");

	while(inpos < size) {
		len = _decode(&Dec_Inst, decoded_data, &data[inpos]);
		fwrite(decoded_data, sizeof(short), len, outcfile);
		inpos += Dec_Inst.no_of_bytes;
		arrayCopyNdx = 0;
		while(arrayCopyNdx*sizeof(short) < len){
			decoded_buffer[outpos+arrayCopyNdx] = decoded_data[arrayCopyNdx];
			arrayCopyNdx++;
		}
		outpos += len*sizeof(short);
		count ++;
	}

	fwrite(decoded_buffer, sizeof(short), 0, outcfile);
	printf("%i\n", outpos);
	PyObject *result = Py_BuildValue("s#", decoded_buffer, outpos*2);
	free(decoded_buffer);
	fclose(outcfile);
	return result;
}

static PyMethodDef methods[] = {
		{ "decode", decode, METH_VARARGS, "Decode a binary stream from ilbc to PCM" },
		{ NULL, NULL },

};

PyMODINIT_FUNC initpy_ilbc_decode(void) {
	PyObject *m;
	m = Py_InitModule("py_ilbc_decode", methods);
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
