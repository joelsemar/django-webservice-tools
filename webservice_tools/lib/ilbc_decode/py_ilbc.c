#include <Python.h>
#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "iLBC_define.h"
#include "iLBC_decode.h"

short decode_prep( /* (o) Number of decoded samples */
		iLBC_Dec_Inst_t *iLBCdec_inst, /* (i/o) Decoder instance */
		short *decoded_data, /* (o) Decoded signal block*/
		short *encoded_data /* (i) Encoded bytes */);

static PyObject *ILBCError;

static PyObject *decode(PyObject *self, PyObject *args) {
	short mode;
	char *data;
	int size;
	short decoded_data[BLOCKL_MAX];  //Where we will store the blocks that have been decoded

	if (!PyArg_ParseTuple(args, "is#", &mode, &data, &size))
		return NULL;

	iLBC_Dec_Inst_t Dec_Inst;  //New Decoder Instance
	initDecode(&Dec_Inst, mode, 1);  //Initialize it with the mode passed in (the last arg means to always
	                                 // use the "enhancer")
	int len = 0;
	int inpos = 0;
	int outpos = 0;

	//create a new buffer to store the decoded data in.  BLOCKL_MAX is the maximum data that can be returned
	//from the decode function.
	int max_data = BLOCKL_MAX*size/Dec_Inst.no_of_bytes*sizeof(short);
	short *decoded_buffer = PyMem_Malloc(max_data);

	int arrayCopyNdx;

	while(inpos < size) {
		len = decode_prep(&Dec_Inst, decoded_data, (short *) &data[inpos]);  //decode the first chunk
		inpos += Dec_Inst.no_of_bytes;  //increment index by size of current decoder's blocks
		arrayCopyNdx = 0;
		while(arrayCopyNdx < len*sizeof(short)){
			decoded_buffer[outpos+arrayCopyNdx] = decoded_data[arrayCopyNdx];
			arrayCopyNdx ++;
		}
		outpos += len;
	}
			//Make a Python Object to return
	PyObject *result = Py_BuildValue("s#", (char *)decoded_buffer, outpos*sizeof(short));
	PyMem_Free(decoded_buffer);  //Free the memory
	return result;
}

static PyMethodDef methods[] = {
		{ "decode", decode, METH_VARARGS, "Decode a binary stream from ilbc to PCM" },
		{ NULL, NULL },

};

PyMODINIT_FUNC initpy_ilbc(void) {
	PyObject *m;
	m = Py_InitModule("py_ilbc", methods);
	if (m == NULL)
		return;

	ILBCError = PyErr_NewException("decode.error", NULL, NULL);
	Py_INCREF(ILBCError);
	PyModule_AddObject(m, "error", ILBCError);

}

short decode_prep( /* (o) Number of decoded samples */
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
