#ifndef NOMINATIM_H
#define NOMINATIM_H

#define MAX(x,y) (x > y?x:y)
#define MIN(x,y) (x < y?x:y)

struct output_options
{
    const char *conninfo;  /* Connection info string */
    const char *prefix;    /* prefix for table names */
    int scale;       /* scale for converting coordinates to fixed point */
    int projection;  /* SRS of projection */
    int append;      /* Append to existing data */
    int slim;        /* In slim mode */
    int cache;       /* Memory usable for cache in MB */
    struct middle_t *mid;  /* Mid storage to use */
    const char *tblsindex;     /* Pg Tablespace to store indexes */
    const char *style;     /* style file to use */
    int expire_tiles_zoom;        /* Zoom level for tile expiry list */
    int expire_tiles_zoom_min;    /* Minimum zoom level for tile expiry list */
    const char *expire_tiles_filename;    /* File name to output expired tiles list to */
    int enable_hstore; /* add an additional hstore column with objects key/value pairs */
    int enable_multi; /* Output multi-geometries intead of several simple geometries */
    char** hstore_columns; /* list of columns that should be written into their own hstore column */
    int n_hstore_columns; /* number of hstore columns */
};

void exit_nicely(void);
void short_usage(char *arg0);

#endif
