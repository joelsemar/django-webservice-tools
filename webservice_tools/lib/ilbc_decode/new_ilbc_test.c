/******************************************************************

 iLBC Speech Coder ANSI-C Source Code

 iLBC_test.c

 Copyright (C) The Internet Society (2004).
 All Rights Reserved.

 ******************************************************************/

#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "iLBC_define.h"
#include "iLBC_encode.h"
#include "iLBC_decode.h"

/* Runtime statistics */
#include <time.h>

#define ILBCNOOFWORDS_MAX   (NO_OF_BYTES_30MS/2)

/*----------------------------------------------------------------*
 *  Decoder interface function
 *---------------------------------------------------------------*/

short decode( /* (o) Number of decoded samples */
iLBC_Dec_Inst_t *iLBCdec_inst, /* (i/o) Decoder instance */
short *decoded_data, /* (o) Decoded signal block*/
short *encoded_data, /* (i) Encoded bytes */
short mode /* (i) 0=PL, 1=Normal */
) {
	int k;
	float decblock[BLOCKL_MAX], dtmp;

	/* check if mode is valid */

	if (mode < 0 || mode > 1) {
		printf("\nERROR - Wrong mode - 0, 1 allowed\n");
		exit(3);
	}

	/* do actual decoding of block */

	iLBC_decode(decblock, (unsigned char *) encoded_data, iLBCdec_inst, mode);

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


int main(int argc, char* argv[]) {

	/* Runtime statistics */

	float starttime;
	float runtime;
	float outtime;

	FILE *efileid, *ofileid;
	short decoded_data[BLOCKL_MAX];
	int len;
	short pli, mode;
	int blockcount = 0;
	int packetlosscount = 0;

	/* Create structs */
	iLBC_Dec_Inst_t Dec_Inst;

	/* get arguments and open files */

	if (argc != 4) {
		fprintf(stderr, "\n*-----------------------------------------------*\n");
		fprintf(stderr, "   %s <20,30> encoded decoded \n\n",
				argv[0]);
		fprintf(stderr, "   mode    : Frame size for the encoding/decoding\n");
		fprintf(stderr, "                 20 - 20 ms\n");
		fprintf(stderr, "                 30 - 30 ms\n");
		fprintf(stderr, "   encoded : Encoded bit stream\n");
		fprintf(stderr, "   decoded : Decoded speech (16-bit pcm file)\n");
		fprintf(stderr, "*-----------------------------------------------*\n\n");
		exit(1);
	}
	mode = atoi(argv[1]);
	if (mode != 20 && mode != 30) {
		fprintf(stderr, "Wrong mode %s, must be 20, or 30\n", argv[1]);
		exit(2);
	}
	if ((efileid = fopen(argv[2], "rb")) == NULL) {
		fprintf(stderr, "Cannot open encoded file %s\n", argv[2]);
		exit(1);
	}
	if ((ofileid = fopen(argv[3], "wb")) == NULL) {
		fprintf(stderr, "Cannot open decoded file %s\n", argv[3]);
		exit(1);
	}

	/* print info */

	fprintf(stderr, "\n");
	fprintf(stderr, "*---------------------------------------------------*\n");
	fprintf(stderr, "*                                                   *\n");
	fprintf(stderr, "*      iLBC test program                            *\n");
	fprintf(stderr, "*                                                   *\n");
	fprintf(stderr, "*                                                   *\n");
	fprintf(stderr, "*---------------------------------------------------*\n");
	fprintf(stderr, "\nMode           : %2d ms\n", mode);
	fprintf(stderr, "Encoded file   : %s\n", argv[2]);
	fprintf(stderr, "Output file    : %s\n", argv[3]);
	fprintf(stderr, "\n");

	/* Initialization */

	initDecode(&Dec_Inst, mode, 1);

	/* Runtime statistics */

	starttime = clock() / (float) CLOCKS_PER_SEC;

	/* loop over input blocks */
	fseek(efileid, 0, SEEK_END);
	int inlen = ftell(efileid);
	int inpos = 0;
	char *input = malloc(inlen);
	fseek(efileid, 0, SEEK_SET);
	fread(input, 1, inlen, efileid);

	while (inpos < inlen) {
		blockcount++;

		/* decoding */

		fprintf(stderr, "--- Decoding block %i --- ", blockcount);

		len = decode(&Dec_Inst, decoded_data, &input[inpos], 1);
		fprintf(stderr, "\r");

		/* write output file */

		fwrite(decoded_data, sizeof(short), len, ofileid);
		inpos += Dec_Inst.no_of_bytes;
	}

	/* Runtime statistics */

	runtime = (float) (clock() / (float) CLOCKS_PER_SEC - starttime);
	outtime = (float) ((float) blockcount * (float) mode / 1000.0);
	printf("\n\nLength of speech file: %.1f s\n", outtime);
	printf("Packet loss          : %.1f%%\n",
			100.0 * (float) packetlosscount / (float) blockcount);

	printf("Time to run iLBC     :");
	printf(" %.1f s (%.1f %% of realtime)\n\n", runtime,
			(100 * runtime / outtime));

	/* close files */

	fclose(efileid);
	fclose(ofileid);
	return (0);
}

