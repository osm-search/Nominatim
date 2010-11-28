#include "postgres.h"
#include "fmgr.h"
#include "mb/pg_wchar.h"
#include <utfasciitable.h>

#ifdef PG_MODULE_MAGIC
PG_MODULE_MAGIC;
#endif

Datum transliteration( PG_FUNCTION_ARGS );
Datum gettokenstring( PG_FUNCTION_ARGS );
void str_replace(char* buffer, int* len, int* changes, char* from, int fromlen, char* to, int tolen, int);
void str_dupspaces(char* buffer);

PG_FUNCTION_INFO_V1( transliteration );
Datum
transliteration( PG_FUNCTION_ARGS )
{
	static char * ascii = UTFASCII;
	static uint16 asciilookup[65536] = UTFASCIILOOKUP;
	char * asciipos;

	text *source;
	unsigned char *sourcedata;
	int sourcedatalength;

        unsigned int c1,c2,c3,c4;
	unsigned int * wchardata;
	unsigned int * wchardatastart;

	text *result;
	unsigned char *resultdata;
	int resultdatalength;
	int iLen;

	if (GetDatabaseEncoding() != PG_UTF8) 
	{
		ereport(ERROR,
                                        (errcode(ERRCODE_FEATURE_NOT_SUPPORTED),
                                         errmsg("requires UTF8 database encoding")));
	}

	if (PG_ARGISNULL(0))
	{
		PG_RETURN_NULL();
	}

	// The original string
	source = PG_GETARG_TEXT_P(0);
	sourcedata = (unsigned char *)VARDATA(source);
	sourcedatalength = VARSIZE(source) - VARHDRSZ;

	// Intermediate wchar version of string
	wchardatastart = wchardata = (unsigned int *)palloc((sourcedatalength+1)*sizeof(int));

	// Based on pg_utf2wchar_with_len from wchar.c
        while (sourcedatalength > 0 && *sourcedata)
        {
                if ((*sourcedata & 0x80) == 0)
                {
                        *wchardata = *sourcedata++;
			wchardata++;
                        sourcedatalength--;
                }
                else if ((*sourcedata & 0xe0) == 0xc0)
                {
                        if (sourcedatalength < 2) break;
                        c1 = *sourcedata++ & 0x1f;
                        c2 = *sourcedata++ & 0x3f;
                        *wchardata = (c1 << 6) | c2;
			wchardata++;
                        sourcedatalength -= 2;
                }
                else if ((*sourcedata & 0xf0) == 0xe0)
                {
                        if (sourcedatalength < 3) break;
                        c1 = *sourcedata++ & 0x0f;
                        c2 = *sourcedata++ & 0x3f;
                        c3 = *sourcedata++ & 0x3f;
                        *wchardata = (c1 << 12) | (c2 << 6) | c3;
			wchardata++;
                        sourcedatalength -= 3;
                }
                else if ((*sourcedata & 0xf8) == 0xf0)
                {
                        if (sourcedatalength < 4) break;
                        c1 = *sourcedata++ & 0x07;
                        c2 = *sourcedata++ & 0x3f;
                        c3 = *sourcedata++ & 0x3f;
                        c4 = *sourcedata++ & 0x3f;
                        *wchardata = (c1 << 18) | (c2 << 12) | (c3 << 6) | c4;
			wchardata++;
                        sourcedatalength -= 4;
                }
                else if ((*sourcedata & 0xfc) == 0xf8)
                {
			// table does not extend beyond 4 char long, just skip
			if (sourcedatalength < 5) break;
			sourcedatalength -= 5;
		}
                else if ((*sourcedata & 0xfe) == 0xfc)
                {
			// table does not extend beyond 4 char long, just skip
			if (sourcedatalength < 6) break;
			sourcedatalength -= 6;
		}
                else
                {
			// assume lenngth 1, silently drop bogus characters
                        sourcedatalength--;
                }
        }
        *wchardata = 0;

	// calc the length of transliteration string
	resultdatalength = 0;
	wchardata = wchardatastart;
	while(*wchardata)
	{
		if (*(asciilookup + *wchardata) > 0) resultdatalength += *(ascii + *(asciilookup + *wchardata));
		wchardata++;
	}

	// allocate & create the result
	result = (text *)palloc(resultdatalength + VARHDRSZ);
	SET_VARSIZE(result, resultdatalength + VARHDRSZ);
	resultdata = (unsigned char *)VARDATA(result);

	wchardata = wchardatastart;
	while(*wchardata)
	{
		if (*(asciilookup + *wchardata) > 0)
		{
			asciipos = ascii + *(asciilookup + *wchardata);
			for(iLen = *asciipos; iLen > 0; iLen--)
			{
				asciipos++;
				*resultdata = *asciipos;
				resultdata++;
			}
		}
		else
		{
			ereport( WARNING, ( errcode( ERRCODE_SUCCESSFUL_COMPLETION ),
		              errmsg( "missing char: %i\n", *wchardata )));
			
		}
		wchardata++;
	}

	pfree(wchardatastart);

	PG_RETURN_TEXT_P(result);
}

void str_replace(char* buffer, int* len, int* changes, char* from, int fromlen, char* to, int tolen, int isspace)
{
        char *p;

        // Search string is too long to be pressent
        if (fromlen > *len) return;

        p = strstr(buffer, from);
        while(p)
        {
                if (!isspace || *(p-1) != ' ')
                {
                        (*changes)++;
                        if (tolen != fromlen) memmove(p+tolen, p+fromlen, *len-(p-buffer)+1);
                        memcpy(p, to, tolen);
                        *len += tolen - fromlen;
                }
                p = strstr(p+1, from);
        }
}

void str_dupspaces(char* buffer)
{
        char *out;
        int wasspace;

        out = buffer;
        wasspace = 0;
        while(*buffer)
        {
                if (wasspace && *buffer != ' ') wasspace = 0;
                if (!wasspace)
                {
                        *out = *buffer;
                        out++;
                        wasspace = (*buffer == ' ');
                }
                buffer++;
        }
        *out = 0;
}

PG_FUNCTION_INFO_V1( gettokenstring );
Datum
gettokenstring( PG_FUNCTION_ARGS )
{
	text *source;
	unsigned char *sourcedata;
	int sourcedatalength;

	char * buffer;
	int len;
	int changes;

	text *result;

	if (GetDatabaseEncoding() != PG_UTF8) 
	{
		ereport(ERROR,
                                        (errcode(ERRCODE_FEATURE_NOT_SUPPORTED),
                                         errmsg("requires UTF8 database encoding")));
	}

	if (PG_ARGISNULL(0))
	{
		PG_RETURN_NULL();
	}

	// The original string
	source = PG_GETARG_TEXT_P(0);
	sourcedata = (unsigned char *)VARDATA(source);
	sourcedatalength = VARSIZE(source) - VARHDRSZ;

	// Buffer for doing the replace in - string could get slightly longer (double is mastive overkill)
	buffer = (char *)palloc((sourcedatalength*2)*sizeof(char));
	memcpy(buffer+1, sourcedata, sourcedatalength);
	buffer[0] = 32;
	buffer[sourcedatalength+1] = 32;
	buffer[sourcedatalength+2] = 0;
	len = sourcedatalength+3;

	changes = 1;
	str_dupspaces(buffer);
	while(changes)
	{
		changes = 0;
		#include <tokenstringreplacements.inc>
		str_dupspaces(buffer);
	}

	// 'and' in various languages
	str_replace(buffer, &len, &changes, " and ", 5, " ", 1, 0);
	str_replace(buffer, &len, &changes, " und ", 5, " ", 1, 0);
	str_replace(buffer, &len, &changes, " en ", 4, " ", 1, 0);
	str_replace(buffer, &len, &changes, " et ", 4, " ", 1, 0);
	str_replace(buffer, &len, &changes, " y ", 3, " ", 1, 0);

	// 'the' (and similar)
	str_replace(buffer, &len, &changes, " the ", 5, " ", 1, 0);
	str_replace(buffer, &len, &changes, " der ", 5, " ", 1, 0);
	str_replace(buffer, &len, &changes, " den ", 5, " ", 1, 0);
	str_replace(buffer, &len, &changes, " die ", 5, " ", 1, 0);
	str_replace(buffer, &len, &changes, " das ", 5, " ", 1, 0);
	str_replace(buffer, &len, &changes, " la ", 4, " ", 1, 0);
	str_replace(buffer, &len, &changes, " le ", 4, " ", 1, 0);
	str_replace(buffer, &len, &changes, " el ", 4, " ", 1, 0);
	str_replace(buffer, &len, &changes, " il ", 4, " ", 1, 0);

	// german
	str_replace(buffer, &len, &changes, "ae", 2, "a", 1, 0);
	str_replace(buffer, &len, &changes, "oe", 2, "o", 1, 0);
	str_replace(buffer, &len, &changes, "ue", 2, "u", 1, 0);
	str_replace(buffer, &len, &changes, "sss", 3, "ss", 2, 0);
	str_replace(buffer, &len, &changes, "ih", 2, "i", 1, 0);
	str_replace(buffer, &len, &changes, "eh", 2, "e", 1, 0);

	// russian
	str_replace(buffer, &len, &changes, "ie", 2, "i", 1, 0);
	str_replace(buffer, &len, &changes, "yi", 2, "i", 1, 0);

	// allocate & create the result
	len--;// Drop the terminating zero
	result = (text *)palloc(len + VARHDRSZ);
	SET_VARSIZE(result, len + VARHDRSZ);
	memcpy(VARDATA(result), buffer, len);

	pfree(buffer);

	PG_RETURN_TEXT_P(result);
}

