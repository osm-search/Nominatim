#define _FILE_OFFSET_BITS 64
#define _LARGEFILE64_SOURCE

#ifdef __MINGW_H
# include <windows.h>
#else
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <zlib.h>
#endif

#include <libxml/xmlreader.h>
#include <bzlib.h>

#include "input.h"

struct Input
{
    char *name;
    enum { plainFile, gzipFile, bzip2File } type;
    void *fileHandle;
    // needed by bzip2 when decompressing from multiple streams. other
    // decompressors must ignore it.
    FILE *systemHandle;
    int eof;
    char buf[4096];
    int buf_ptr, buf_fill;
};

// tries to re-open the bz stream at the next stream start.
// returns 0 on success, -1 on failure.
int bzReOpen(struct Input *ctx, int *error)
{
    // for copying out the last unused part of the block which
    // has an EOS token in it. needed for re-initialising the
    // next stream.
    unsigned char unused[BZ_MAX_UNUSED];
    void *unused_tmp_ptr = NULL;
    int nUnused, i;

    BZ2_bzReadGetUnused(error, (BZFILE *)(ctx->fileHandle), &unused_tmp_ptr, &nUnused);
    if (*error != BZ_OK) return -1;

    // when bzReadClose is called the unused buffer is deallocated,
    // so it needs to be copied somewhere safe first.
    for (i = 0; i < nUnused; ++i)
        unused[i] = ((unsigned char *)unused_tmp_ptr)[i];

    BZ2_bzReadClose(error, (BZFILE *)(ctx->fileHandle));
    if (*error != BZ_OK) return -1;

    // reassign the file handle
    ctx->fileHandle = BZ2_bzReadOpen(error, ctx->systemHandle, 0, 0, unused, nUnused);
    if (ctx->fileHandle == NULL || *error != BZ_OK) return -1;

    return 0;
}

int readFile(void *context, char * buffer, int len)
{
    struct Input *ctx = context;
    void *f = ctx->fileHandle;
    int l = 0, error = 0;

    if (ctx->eof || (len == 0))
        return 0;

    switch (ctx->type)
    {
    case plainFile:
        l = read(*(int *)f, buffer, len);
        if (l <= 0) ctx->eof = 1;
        break;
    case gzipFile:
        l = gzread((gzFile)f, buffer, len);
        if (l <= 0) ctx->eof = 1;
        break;
    case bzip2File:
        l = BZ2_bzRead(&error, (BZFILE *)f, buffer, len);

        // error codes BZ_OK and BZ_STREAM_END are both "OK", but the stream
        // end means the reader needs to be reset from the original handle.
        if (error != BZ_OK)
        {
            // for stream errors, try re-opening the stream before admitting defeat.
            if (error != BZ_STREAM_END || bzReOpen(ctx, &error) != 0)
            {
                l = 0;
                ctx->eof = 1;
            }
        }
        break;
    default:
        fprintf(stderr, "Bad file type\n");
        break;
    }

    if (l < 0)
    {
        fprintf(stderr, "File reader received error %d (%d)\n", l, error);
        l = 0;
    }

    return l;
}

char inputGetChar(void *context)
{
    struct Input *ctx = context;

    if (ctx->buf_ptr == ctx->buf_fill)
    {
        ctx->buf_fill = readFile(context, &ctx->buf[0], sizeof(ctx->buf));
        ctx->buf_ptr = 0;
        if (ctx->buf_fill == 0)
            return 0;
        if (ctx->buf_fill < 0)
        {
            perror("Error while reading file");
            exit(1);
        }
    }
    //readFile(context, &c, 1);
    return ctx->buf[ctx->buf_ptr++];
}

int inputEof(void *context)
{
    return ((struct Input *)context)->eof;
}

void *inputOpen(const char *name)
{
    const char *ext = strrchr(name, '.');
    struct Input *ctx = malloc (sizeof(*ctx));

    if (!ctx)
        return NULL;

    memset(ctx, 0, sizeof(*ctx));

    ctx->name = strdup(name);

    if (ext && !strcmp(ext, ".gz"))
    {
        ctx->fileHandle = (void *)gzopen(name, "rb");
        ctx->type = gzipFile;
    }
    else if (ext && !strcmp(ext, ".bz2"))
    {
        int error = 0;
        ctx->systemHandle = fopen(name, "rb");
        if (!ctx->systemHandle)
        {
            fprintf(stderr, "error while opening file %s\n", name);
            exit(10);
        }

        ctx->fileHandle = (void *)BZ2_bzReadOpen(&error, ctx->systemHandle, 0, 0, NULL, 0);
        ctx->type = bzip2File;

    }
    else
    {
        int *pfd = malloc(sizeof(pfd));
        if (pfd)
        {
            if (!strcmp(name, "-"))
            {
                *pfd = STDIN_FILENO;
            }
            else
            {
                int flags = O_RDONLY;
#ifdef O_LARGEFILE
                flags |= O_LARGEFILE;
#endif
                *pfd = open(name, flags);
                if (*pfd < 0)
                {
                    free(pfd);
                    pfd = NULL;
                }
            }
        }
        ctx->fileHandle = (void *)pfd;
        ctx->type = plainFile;
    }
    if (!ctx->fileHandle)
    {
        fprintf(stderr, "error while opening file %s\n", name);
        exit(10);
    }
    ctx->buf_ptr = 0;
    ctx->buf_fill = 0;
    return (void *)ctx;
}

int inputClose(void *context)
{
    struct Input *ctx = context;
    void *f = ctx->fileHandle;

    switch (ctx->type)
    {
    case plainFile:
        close(*(int *)f);
        free(f);
        break;
    case gzipFile:
        gzclose((gzFile)f);
        break;
    case bzip2File:
        BZ2_bzclose((BZFILE *)f);
        break;
    default:
        fprintf(stderr, "Bad file type\n");
        break;
    }

    free(ctx->name);
    free(ctx);
    return 0;
}

xmlTextReaderPtr inputUTF8(const char *name)
{
    void *ctx = inputOpen(name);

    if (!ctx)
    {
        fprintf(stderr, "Input reader create failed for: %s\n", name);
        return NULL;
    }

    return xmlReaderForIO(readFile, inputClose, (void *)ctx, NULL, NULL, 0);
}
