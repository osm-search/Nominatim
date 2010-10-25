/*
* The author of this software is Shane O'Sullivan.  
* Permission to use, copy, modify, and distribute this software for any
* purpose without fee is hereby granted, provided that this entire notice
* is included in all copies of any software which is or includes a copy
* or modification of this software and in all copies of the supporting
* documentation for such software.
* THIS SOFTWARE IS BEING PROVIDED "AS IS", WITHOUT ANY EXPRESS OR IMPLIED
* WARRANTY.  IN PARTICULAR, NEITHER THE AUTHORS NOR AT&T MAKE ANY
* REPRESENTATION OR WARRANTY OF ANY KIND CONCERNING THE MERCHANTABILITY
* OF THIS SOFTWARE OR ITS FITNESS FOR ANY PARTICULAR PURPOSE.
*/


#
#include <stdio.h>
#include <search.h>
#include <malloc.h>
#include "VoronoiDiagramGenerator.h"



int main(int argc, char **argv) 
{	
        double xmin, xmax, ymin, ymax;
        scanf("%lf %lf %lf %lf", &xmin, &xmax, &ymin, &ymax) ;

        SourcePoint * sites;
        long nsites;

        nsites = 0;
        sites = (SourcePoint *) malloc(4000 * sizeof(SourcePoint));
        while (scanf("%d %lf %lf %lf", &sites[nsites].id, &sites[nsites].weight, &sites[nsites].x, &sites[nsites].y) != EOF)
        {
                nsites++;
                if (nsites % 4000 == 0) {
                        sites = (SourcePoint *)realloc(sites,(nsites+4000)*sizeof(SourcePoint));
                }
        }

        VoronoiDiagramGenerator * pvdg;
        pvdg = new VoronoiDiagramGenerator();
        pvdg->generateVoronoi(sites, nsites, xmin, xmax, ymin, ymax, 0);

//	printf("sites %ld\n-------------------------------\n", nsites);
        PolygonPoint* pSitePoints;
        int numpoints, i, j;
        for(i = 0; i < nsites; i++)
        {
                pvdg->getSitePoints(i, &numpoints, &pSitePoints);
                if (numpoints == 0)
                {
                        printf("-- no points for %d\n", i);
                }
                else
                {


                        printf("update temp_child_4076440_0 set resultgeom = st_setsrid('POLYGON((");
                        for(j = 0; j < numpoints; j++)
                        {
                                printf("%.15lf %.15lf,", pSitePoints[j].coord.x, pSitePoints[j].coord.y, (pSitePoints[j].angle/M_PI)*180);
                        }
                        printf("%.15lf %.15lf", pSitePoints[0].coord.x, pSitePoints[0].coord.y, (pSitePoints[j].angle/M_PI)*180);
                        printf("))'::geometry,4326) where id = %d;\n", sites[i].id);

                }
        }

	float x1,y1,x2,y2;
//	printf("sites %ld\n-------------------------------\n", nsites);
	pvdg->resetIterator();
	while(pvdg->getNext(x1,y1,x2,y2))
	{
		printf("(%f %f,%f %f)\n",x1,y1,x2, y2);
		
	}

        delete pvdg;
        free(sites);

	return 0;
}



