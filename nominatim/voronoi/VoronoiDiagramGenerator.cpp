/*
* The author of this software is Steven Fortune.  Copyright (c) 1994 by AT&T
* Bell Laboratories.
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

/* 
* This code was originally written by Stephan Fortune in C code.  I, Shane O'Sullivan, 
* have since modified it, encapsulating it in a C++ class and, fixing memory leaks and 
* adding accessors to the Voronoi Edges.
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

#include "VoronoiDiagramGenerator.h"
#include <stdio.h>
#include <sys/mman.h>

VoronoiDiagramGenerator::VoronoiDiagramGenerator()
{
	siteidx = 0;
	sites = 0;

	allMemoryList = new FreeNodeArrayList;
	allMemoryList->memory = 0;
	allMemoryList->next = 0;
	currentMemoryBlock = allMemoryList;
	allEdges = 0;
	iteratorEdges = 0;
	minDistanceBetweenSites = 0;
}

VoronoiDiagramGenerator::~VoronoiDiagramGenerator()
{
	cleanup();
	cleanupEdges();

	if(allMemoryList != 0)
		delete allMemoryList;
}

bool VoronoiDiagramGenerator::generateVoronoi(struct SourcePoint* srcPoints, int numPoints, float minX, float maxX, float minY, float maxY, float minDist)
{
	cleanup();
	cleanupEdges();
	int i;

	minDistanceBetweenSites = minDist;

	nsites = numPoints;
	plot = 0;
	triangulate = 0;
	debug = 1;
	sorted = 0;
	freeinit(&sfl, sizeof (Site));

	sites = (struct Site *) myalloc(nsites * sizeof(*sites));
	polygons = (struct Polygon *) myalloc(nsites * sizeof(*polygons));

	if(sites == 0) return false;

        xmin = srcPoints[0].x;
        ymin = srcPoints[0].y;
        xmax = srcPoints[0].x;
        ymax = srcPoints[0].y;

        for(i = 0; i < nsites; i++)
        {
                sites[i].coord.x = srcPoints[i].x;
                sites[i].coord.y = srcPoints[i].y;
                sites[i].weight = srcPoints[i].weight;
                sites[i].sitenbr = i;
                sites[i].refcnt = 0; // prevent reuse?

                if(sites[i].coord.x < xmin)
                        xmin = sites[i].coord.x;
                else if(sites[i].coord.x > xmax)
                        xmax = sites[i].coord.x;

                if(sites[i].coord.y < ymin)
                        ymin = sites[i].coord.y;
                else if(sites[i].coord.y > ymax)
                        ymax = sites[i].coord.y;

		polygons[i].coord.x = sites[i].coord.x;
		polygons[i].coord.y = sites[i].coord.y;
		polygons[i].numpoints = 0;
		polygons[i].pointlist = NULL;
		polygons[i].boundary = 0;

                //printf("\n%lf %lf\n", sites[i].coord.x, sites[i].coord.y);
        }

	qsort(sites, nsites, sizeof (*sites), scomp);

	siteidx = 0;
	geominit();
	float temp = 0;
	if(minX > maxX)
	{
		temp = minX;
		minX = maxX;
		maxX = temp;
	}
	if(minY > maxY)
	{
		temp = minY;
		minY = maxY;
		maxY = temp;
	}
	borderMinX = minX;
	borderMinY = minY;
	borderMaxX = maxX;
	borderMaxY = maxY;

	corners[0].x = borderMinX;
        corners[0].y = borderMinY;
        corners[1].x = borderMinX;
        corners[1].y = borderMaxY;
        corners[2].x = borderMaxX;
        corners[2].y = borderMaxY;
        corners[3].x = borderMaxX;
        corners[3].y = borderMinY;

	siteidx = 0;
	voronoi(triangulate);

	return true;
}

bool VoronoiDiagramGenerator::ELinitialize()
{
	int i;
	freeinit(&hfl, sizeof **ELhash);
	ELhashsize = 2 * sqrt_nsites;
	ELhash = (struct Halfedge **) myalloc ( sizeof *ELhash * ELhashsize);

	if(ELhash == 0)
		return false;

	for(i=0; i<ELhashsize; i +=1) ELhash[i] = (struct Halfedge *)NULL;
	ELleftend = HEcreate( (struct Edge *)NULL, 0);
	ELrightend = HEcreate( (struct Edge *)NULL, 0);
	ELleftend -> ELleft = (struct Halfedge *)NULL;
	ELleftend -> ELright = ELrightend;
	ELrightend -> ELleft = ELleftend;
	ELrightend -> ELright = (struct Halfedge *)NULL;
	ELhash[0] = ELleftend;
	ELhash[ELhashsize-1] = ELrightend;

	return true;
}


struct Halfedge* VoronoiDiagramGenerator::HEcreate(struct Edge *e,int pm)
{
	struct Halfedge *answer;
	answer = (struct Halfedge *) getfree(&hfl);
	answer -> ELedge = e;
	answer -> ELpm = pm;
	answer -> PQnext = (struct Halfedge *) NULL;
	answer -> vertex = (struct Site *) NULL;
	answer -> ELrefcnt = 0;
	return(answer);
}


void VoronoiDiagramGenerator::ELinsert(struct	Halfedge *lb, struct Halfedge *newHe)
{
	newHe -> ELleft = lb;
	newHe -> ELright = lb -> ELright;
	(lb -> ELright) -> ELleft = newHe;
	lb -> ELright = newHe;
}

/* Get entry from hash table, pruning any deleted nodes */
struct Halfedge * VoronoiDiagramGenerator::ELgethash(int b)
{
	struct Halfedge *he;

	if(b<0 || b>=ELhashsize)
		return((struct Halfedge *) NULL);
	he = ELhash[b];
	if (he == (struct Halfedge *) NULL || he->ELedge != (struct Edge *) DELETED )
		return (he);

	/* Hash table points to deleted half edge.  Patch as necessary. */
	ELhash[b] = (struct Halfedge *) NULL;
	if ((he -> ELrefcnt -= 1) == 0) 
		makefree((Freenode*)he, &hfl);
	return ((struct Halfedge *) NULL);
}

struct Halfedge * VoronoiDiagramGenerator::ELleftbnd(struct Point *p)
{
	int i, bucket;
	struct Halfedge *he;

	/* Use hash table to get close to desired halfedge */
	bucket = (int)((p->x - xmin)/deltax * ELhashsize);	//use the hash function to find the place in the hash map that this HalfEdge should be

	if(bucket<0) bucket =0;					//make sure that the bucket position in within the range of the hash array
	if(bucket>=ELhashsize) bucket = ELhashsize - 1;

	he = ELgethash(bucket);
	if(he == (struct Halfedge *) NULL)			//if the HE isn't found, search backwards and forwards in the hash map for the first non-null entry
	{
		for(i=1; 1 ; i += 1)
		{
			if ((he=ELgethash(bucket-i)) != (struct Halfedge *) NULL)
				break;
			if ((he=ELgethash(bucket+i)) != (struct Halfedge *) NULL)
				break;
		};
		totalsearch += i;
	};
	ntry += 1;
	/* Now search linear list of halfedges for the correct one */
	if (he==ELleftend  || (he != ELrightend && right_of(he,p)))
	{
		do 
		{
			he = he -> ELright;
		} while (he!=ELrightend && right_of(he,p));	//keep going right on the list until either the end is reached, or you find the 1st edge which the point
		he = he -> ELleft;				//isn't to the right of
	}
	else 							//if the point is to the left of the HalfEdge, then search left for the HE just to the left of the point
		do
		{
			he = he -> ELleft;
		} while (he!=ELleftend && !right_of(he,p));

	/* Update hash table and reference counts */
	if(bucket > 0 && bucket <ELhashsize-1)
	{
		if(ELhash[bucket] != (struct Halfedge *) NULL) 
		{
			ELhash[bucket] -> ELrefcnt -= 1;
		}
		ELhash[bucket] = he;
		ELhash[bucket] -> ELrefcnt += 1;
	};
	return (he);
}


/* This delete routine can't reclaim node, since pointers from hash
table may be present.   */
void VoronoiDiagramGenerator::ELdelete(struct Halfedge *he)
{
	(he -> ELleft) -> ELright = he -> ELright;
	(he -> ELright) -> ELleft = he -> ELleft;
	he -> ELedge = (struct Edge *)DELETED;
}


struct Halfedge * VoronoiDiagramGenerator::ELright(struct Halfedge *he)
{
	return (he -> ELright);
}

struct Halfedge * VoronoiDiagramGenerator::ELleft(struct Halfedge *he)
{
	return (he -> ELleft);
}


struct Site * VoronoiDiagramGenerator::leftreg(struct Halfedge *he)
{
	if(he -> ELedge == (struct Edge *)NULL)
		return(bottomsite);
	return( he -> ELpm == le ?
		he -> ELedge -> reg[le] : he -> ELedge -> reg[re]);
}

struct Site * VoronoiDiagramGenerator::rightreg(struct Halfedge *he)
{
	if(he -> ELedge == (struct Edge *)NULL) //if this halfedge has no edge, return the bottom site (whatever that is)
		return(bottomsite);

	//if the ELpm field is zero, return the site 0 that this edge bisects, otherwise return site number 1
	return( he -> ELpm == le ? he -> ELedge -> reg[re] : he -> ELedge -> reg[le]);
}

void VoronoiDiagramGenerator::geominit()
{
	float sn;

	freeinit(&efl, sizeof(Edge));
	nvertices = 0;
	nedges = 0;
	sn = (float)nsites+4;
	sqrt_nsites = (int)sqrt(sn);
	deltay = ymax - ymin;
	deltax = xmax - xmin;
}


struct Edge * VoronoiDiagramGenerator::bisect(struct Site *s1,struct	Site *s2)
{
	float dx,dy,adx,ady;
	struct Edge *newedge;

	newedge = (struct Edge *) getfree(&efl);

	newedge -> reg[0] = s1; //store the sites that this edge is bisecting
	newedge -> reg[1] = s2;
	ref(s1);
	ref(s2);
	newedge -> ep[0] = (struct Site *) NULL; //to begin with, there are no endpoints on the bisector - it goes to infinity
	newedge -> ep[1] = (struct Site *) NULL;

	dx = s2->coord.x - s1->coord.x;			//get the difference in x dist between the sites
	dy = s2->coord.y - s1->coord.y;
	adx = dx>0 ? dx : -dx;					//make sure that the difference in positive
	ady = dy>0 ? dy : -dy;
	newedge -> c = (float)(s1->coord.x * dx + s1->coord.y * dy + (dx*dx + dy*dy)*0.5);//get the slope of the line

	if (adx>ady)
	{
		newedge -> a = 1.0; newedge -> b = dy/dx; newedge -> c /= dx;//set formula of line, with x fixed to 1
	}
	else
	{
		newedge -> b = 1.0; newedge -> a = dx/dy; newedge -> c /= dy;//set formula of line, with y fixed to 1
	};

	newedge -> edgenbr = nedges;

	//printf("\nbisect(%d) ((%f,%f) and (%f,%f)",nedges,s1->coord.x,s1->coord.y,s2->coord.x,s2->coord.y);

	nedges += 1;
	return(newedge);
}

//create a new site where the HalfEdges el1 and el2 intersect - note that the Point in the argument list is not used, don't know why it's there
struct Site * VoronoiDiagramGenerator::intersect(struct Halfedge *el1, struct Halfedge *el2, struct Point *p)
{
	struct	Edge *e1,*e2, *e;
	struct  Halfedge *el;
	float d, xint, yint;
	int right_of_site;
	struct Site *v;

	e1 = el1 -> ELedge;
	e2 = el2 -> ELedge;
	if(e1 == (struct Edge*)NULL || e2 == (struct Edge*)NULL)
		return ((struct Site *) NULL);

	//if the two edges bisect the same parent, return null
	if (e1->reg[1] == e2->reg[1])
		return ((struct Site *) NULL);

	d = e1->a * e2->b - e1->b * e2->a;
	if (-1.0e-10<d && d<1.0e-10)
		return ((struct Site *) NULL);

	xint = (e1->c*e2->b - e2->c*e1->b)/d;
	yint = (e2->c*e1->a - e1->c*e2->a)/d;

	if( (e1->reg[1]->coord.y < e2->reg[1]->coord.y) ||
		(e1->reg[1]->coord.y == e2->reg[1]->coord.y &&
		e1->reg[1]->coord.x < e2->reg[1]->coord.x) )
	{
		el = el1;
		e = e1;
	}
	else
	{
		el = el2;
		e = e2;
	};

	right_of_site = xint >= e -> reg[1] -> coord.x;
	if ((right_of_site && el -> ELpm == le) || (!right_of_site && el -> ELpm == re))
		return ((struct Site *) NULL);

	//create a new site at the point of intersection - this is a new vector event waiting to happen
	v = (struct Site *) getfree(&sfl);
	v -> refcnt = 0;
	v -> coord.x = xint;
	v -> coord.y = yint;
	return(v);
}

/* returns 1 if p is to right of halfedge e */
int VoronoiDiagramGenerator::right_of(struct Halfedge *el,struct Point *p)
{
	struct Edge *e;
	struct Site *topsite;
	int right_of_site, above, fast;
	float dxp, dyp, dxs, t1, t2, t3, yl;

	e = el -> ELedge;
	topsite = e -> reg[1];
	right_of_site = p -> x > topsite -> coord.x;
	if(right_of_site && el -> ELpm == le) return(1);
	if(!right_of_site && el -> ELpm == re) return (0);
	if (e->a == 1.0)
	{
		dyp = p->y - topsite->coord.y;
		dxp = p->x - topsite->coord.x;
		fast = 0;
		if ((!right_of_site & (e->b<0.0)) | (right_of_site & (e->b>=0.0)) )
		{
			above = dyp>= e->b*dxp;
			fast = above;
		}
		else
		{
			above = p->x + p->y*e->b > e-> c;
			if(e->b<0.0) above = !above;
			if (!above) fast = 1;
		}

		if (!fast)
		{
			dxs = topsite->coord.x - (e->reg[0])->coord.x;
			above = e->b * (dxp*dxp - dyp*dyp) <
			dxs*dyp*(1.0+2.0*dxp/dxs + e->b*e->b);
			if(e->b<0.0) above = !above;
		}
	}
	else  /*e->b==1.0 */
	{
		yl = e->c - e->a*p->x;
		t1 = p->y - yl;
		t2 = p->x - topsite->coord.x;
		t3 = yl - topsite->coord.y;
		above = t1*t1 > t2*t2 + t3*t3;
	}
	return (el->ELpm==le ? above : !above);
}


void VoronoiDiagramGenerator::endpoint(struct Edge *e,int lr,struct Site * s)
{
	e -> ep[lr] = s;
	ref(s);
	return;

	if(e -> ep[re-lr]== (struct Site *) NULL)
		return;

	clip_line(e);

	deref(e->reg[le]);
	deref(e->reg[re]);
	makefree((Freenode*)e, &efl);
}

void VoronoiDiagramGenerator::endpoint(struct Edge *e1,int lr,struct Site * s, struct Edge *e2, struct Edge *e3)
{
	e1 -> ep[lr] = s;
	ref(s);

	s->coordout.x = s->coord.x;
	s->coordout.y = s->coord.y;

        if(e1 -> ep[le] != (struct Site *) NULL && e1 -> ep[re] != (struct Site *) NULL)
        {
                clip_line(e1);
                deref(e1->reg[le]);
                deref(e1->reg[re]);
                makefree((Freenode*)e1, &efl);
        }

        if(e2 -> ep[le] != (struct Site *) NULL && e2 -> ep[re] != (struct Site *) NULL)
        {
                clip_line(e2);
                deref(e2->reg[le]);
                deref(e2->reg[re]);
                makefree((Freenode*)e2, &efl);
        }

        if(e3 -> ep[le] != (struct Site *) NULL && e3 -> ep[re] != (struct Site *) NULL)
        {
                clip_line(e3);
                deref(e3->reg[le]);
                deref(e3->reg[re]);
                makefree((Freenode*)e3, &efl);
        }

	return;	
}


float VoronoiDiagramGenerator::dist(struct Site *s,struct Site *t)
{
	float dx,dy;
	dx = s->coord.x - t->coord.x;
	dy = s->coord.y - t->coord.y;
	return (float)(sqrt(dx*dx + dy*dy));
}


void VoronoiDiagramGenerator::makevertex(struct Site *v)
{
	v -> sitenbr = nvertices;
	nvertices += 1;
	out_vertex(v);
}


void VoronoiDiagramGenerator::deref(struct Site *v)
{
	v -> refcnt -= 1;
	if (v -> refcnt == 0 ) 
		makefree((Freenode*)v, &sfl);
}

void VoronoiDiagramGenerator::ref(struct Site *v)
{
	v -> refcnt += 1;
}

//push the HalfEdge into the ordered linked list of vertices
void VoronoiDiagramGenerator::PQinsert(struct Halfedge *he,struct Site * v, float offset)
{
	struct Halfedge *last, *next;

	he -> vertex = v;
	ref(v);
	he -> ystar = (float)(v -> coord.y + offset);
	last = &PQhash[PQbucket(he)];
	while ((next = last -> PQnext) != (struct Halfedge *) NULL &&
		(he -> ystar  > next -> ystar  ||
		(he -> ystar == next -> ystar && v -> coord.x > next->vertex->coord.x)))
	{
		last = next;
	}
	he -> PQnext = last -> PQnext;
	last -> PQnext = he;
	PQcount += 1;
}

//remove the HalfEdge from the list of vertices
void VoronoiDiagramGenerator::PQdelete(struct Halfedge *he)
{
	struct Halfedge *last;

	if(he -> vertex != (struct Site *) NULL)
	{
		last = &PQhash[PQbucket(he)];
		while (last -> PQnext != he)
			last = last -> PQnext;

		last -> PQnext = he -> PQnext;
		PQcount -= 1;
		deref(he -> vertex);
		he -> vertex = (struct Site *) NULL;
	};
}

int VoronoiDiagramGenerator::PQbucket(struct Halfedge *he)
{
	int bucket;

	bucket = (int)((he->ystar - ymin)/deltay * PQhashsize);
	if (bucket<0) bucket = 0;
	if (bucket>=PQhashsize) bucket = PQhashsize-1 ;
	if (bucket < PQmin) PQmin = bucket;
	return(bucket);
}

int VoronoiDiagramGenerator::PQempty()
{
	return(PQcount==0);
}


struct Point VoronoiDiagramGenerator::PQ_min()
{
	struct Point answer;

	while(PQhash[PQmin].PQnext == (struct Halfedge *)NULL) {PQmin += 1;};
	answer.x = PQhash[PQmin].PQnext -> vertex -> coord.x;
	answer.y = PQhash[PQmin].PQnext -> ystar;
	return (answer);
}

struct Halfedge * VoronoiDiagramGenerator::PQextractmin()
{
	struct Halfedge *curr;

	curr = PQhash[PQmin].PQnext;
	PQhash[PQmin].PQnext = curr -> PQnext;
	PQcount -= 1;
	return(curr);
}


bool VoronoiDiagramGenerator::PQinitialize()
{
	int i;

	PQcount = 0;
	PQmin = 0;
	PQhashsize = 4 * sqrt_nsites;
	PQhash = (struct Halfedge *) myalloc(PQhashsize * sizeof *PQhash);

	if(PQhash == 0)
		return false;

	for(i=0; i<PQhashsize; i+=1) PQhash[i].PQnext = (struct Halfedge *)NULL;

	return true;
}


void VoronoiDiagramGenerator::freeinit(struct Freelist *fl,int size)
{
	fl -> head = (struct Freenode *) NULL;
	fl -> nodesize = size;
}

char * VoronoiDiagramGenerator::getfree(struct Freelist *fl)
{
	int i;
	struct Freenode *t;

	if(fl->head == (struct Freenode *) NULL)
	{
		t =  (struct Freenode *) myalloc(sqrt_nsites * fl->nodesize);

		if(t == 0)
			return 0;

		currentMemoryBlock->next = new FreeNodeArrayList;
		currentMemoryBlock = currentMemoryBlock->next;
		currentMemoryBlock->memory = t;
		currentMemoryBlock->next = 0;

		for(i=0; i<sqrt_nsites; i+=1)
			makefree((struct Freenode *)((char *)t+i*fl->nodesize), fl);
	};
	t = fl -> head;
	fl -> head = (fl -> head) -> nextfree;
	return((char *)t);
}



void VoronoiDiagramGenerator::makefree(struct Freenode *curr,struct Freelist *fl)
{
	curr -> nextfree = fl -> head;
	fl -> head = curr;
}

void VoronoiDiagramGenerator::cleanup()
{
	if(sites != 0)
	{
		free(sites);
		sites = 0;
	}

	FreeNodeArrayList* current=0, *prev = 0;

	current = prev = allMemoryList;

	while(current->next != 0)
	{
		prev = current;
		current = current->next;
		free(prev->memory);
		delete prev;
		prev = 0;
	}

	if(current != 0 && current->memory != 0)
	{
		free(current->memory);
		delete current;
	}

	allMemoryList = new FreeNodeArrayList;
	allMemoryList->next = 0;
	allMemoryList->memory = 0;
	currentMemoryBlock = allMemoryList;
}

void VoronoiDiagramGenerator::cleanupEdges()
{
	GraphEdge* geCurrent = 0, *gePrev = 0;
	geCurrent = gePrev = allEdges;

	while(geCurrent != 0 && geCurrent->next != 0)
	{
		gePrev = geCurrent;
		geCurrent = geCurrent->next;
		delete gePrev;
	}

	allEdges = 0;

}

void VoronoiDiagramGenerator::pushGraphEdge(float x1, float y1, float x2, float y2)
{
	GraphEdge* newEdge = new GraphEdge;
	newEdge->next = allEdges;
	allEdges = newEdge;
	newEdge->x1 = x1;
	newEdge->y1 = y1;
	newEdge->x2 = x2;
	newEdge->y2 = y2;
}


char * VoronoiDiagramGenerator::myalloc(unsigned n)
{
	char *t=0;
	t=(char*)malloc(n);
	total_alloc += n;
	return(t);
}


/* for those who don't have Cherry's plot */
/* #include <plot.h> */
void VoronoiDiagramGenerator::openpl(){}
void VoronoiDiagramGenerator::line(float x1, float y1, float x2, float y2)
{
	pushGraphEdge(x1,y1,x2,y2);

}
void VoronoiDiagramGenerator::circle(float x, float y, float radius){}
void VoronoiDiagramGenerator::range(float minX, float minY, float maxX, float maxY){}



void VoronoiDiagramGenerator::out_bisector(struct Edge *e)
{

}


void VoronoiDiagramGenerator::out_ep(struct Edge *e)
{

}

void VoronoiDiagramGenerator::out_vertex(struct Site *v)
{

}


void VoronoiDiagramGenerator::out_site(struct Site *s)
{
	if(!triangulate & plot & !debug)
		circle (s->coord.x, s->coord.y, cradius);
}


void VoronoiDiagramGenerator::out_triple(struct Site *s1, struct Site *s2,struct Site * s3)
{

}



void VoronoiDiagramGenerator::plotinit()
{
	float dx,dy,d;

	dy = ymax - ymin;
	dx = xmax - xmin;
	d = (float)(( dx > dy ? dx : dy) * 1.1);
	pxmin = (float)(xmin - (d-dx)/2.0);
	pxmax = (float)(xmax + (d-dx)/2.0);
	pymin = (float)(ymin - (d-dy)/2.0);
	pymax = (float)(ymax + (d-dy)/2.0);
	cradius = (float)((pxmax - pxmin)/350.0);
	openpl();
	range(pxmin, pymin, pxmax, pymax);
}

void VoronoiDiagramGenerator::pushpoint(int sitenbr, double x, double y, int boundary)
{
	Polygon *s;

	s = &polygons[sitenbr];

        if (s->numpoints == 0)
        {
                s->pointlist = (PolygonPoint *)malloc(sizeof(struct PolygonPoint)*(s->numpoints+10));
                if (!s->pointlist)
                {
                        printf("Out of mem\n");
                }
        }
        else if (s->numpoints % 10 == 0)
        {
                s->pointlist = (PolygonPoint *)realloc(s->pointlist, sizeof(struct PolygonPoint)*(s->numpoints+10));
                if (!s->pointlist)
                {
                        printf("Out of remem\n");
                }
        }
        s->pointlist[s->numpoints].coord.x = x;
        s->pointlist[s->numpoints].coord.y = y;
        s->pointlist[s->numpoints].angle = atan2f(x-s->coord.x, y-s->coord.y);
	s->pointlist[s->numpoints].boundary = boundary;

	if (boundary) s->boundary = 1;

        //printf("point #%d in %d (%lf, %lf) [%d] (%lf, %lf): %lf\n", s->numpoints, sitenbr, s->coord.x, s->coord.y, boundary, x, y, (s->pointlist[s->numpoints].angle/M_PI)*180);

        s->numpoints++;
}

int VoronoiDiagramGenerator::ccw( Point p0, Point p1, Point p2 )
{
	double dx1, dx2, dy1, dy2;

	dx1 = p1.x - p0.x; dy1 = p1.y - p0.y;
	dx2 = p2.x - p0.x; dy2 = p2.y - p0.y;

	if (dx1*dy2 > dy1*dx2)
		return +1;
	if (dx1*dy2 < dy1*dx2)
		return -1;
	if ((dx1*dx2 < 0) || (dy1*dy2 < 0))
		return -1;
	if ((dx1*dx1 + dy1*dy1) < (dx2*dx2 + dy2*dy2))
		return +1;
	return 0;
}

void VoronoiDiagramGenerator::getSitePoints(int sitenbr, int* numpoints, PolygonPoint** pS)
{
	int i, j, c, any, centrevalue, cornerinpolygon[4];

	if (polygons[sitenbr].numpoints == 0)
	{
		for(c = 0; c < 4; c++)
		{
			pushpoint(sitenbr, corners[c].x, corners[c].y, 0);
		}
	}

        qsort(polygons[sitenbr].pointlist, polygons[sitenbr].numpoints, sizeof(PolygonPoint), anglecomp);

	if (polygons[sitenbr].boundary)
	{
//		printf("\nsite %d is boundary intersection\n", sitenbr);

		for(c = 0; c < 4; c++) cornerinpolygon[c] = 1;

		for(i = 0; i < polygons[sitenbr].numpoints; i++)
		{
//			printf("Point (%lf,%lf) %d\n", polygons[sitenbr].pointlist[i].coord.x,polygons[sitenbr].pointlist[i].coord.y,polygons[sitenbr].pointlist[i].boundary);
			j = i > 0?i-1:polygons[sitenbr].numpoints-1;
			if (	(!polygons[sitenbr].pointlist[i].boundary || !polygons[sitenbr].pointlist[j].boundary) &&
				(polygons[sitenbr].pointlist[i].coord.x != polygons[sitenbr].pointlist[j].coord.x ||
				polygons[sitenbr].pointlist[i].coord.y != polygons[sitenbr].pointlist[j].coord.y))
			{
//				printf("line side test (%lf,%lf) => (%lf,%lf)\n",polygons[sitenbr].pointlist[i].coord.x,polygons[sitenbr].pointlist[i].coord.y,polygons[sitenbr].pointlist[j].coord.x,polygons[sitenbr].pointlist[j].coord.y);
				any = 0;
				centrevalue = ccw(polygons[sitenbr].pointlist[i].coord, polygons[sitenbr].pointlist[j].coord, polygons[sitenbr].coord);
//printf(" test against centre (%lf,%lf) %d\n", polygons[sitenbr].coord.x, polygons[sitenbr].coord.y, centrevalue);
				for(c = 0; c < 4; c++)
				{
					if (cornerinpolygon[c])
					{

//printf(" test against corner (%lf,%lf) %d\n", corners[c].x, corners[c].y, ccw(polygons[sitenbr].pointlist[i].coord, polygons[sitenbr].pointlist[j].coord, corners[c]));

						if (centrevalue == ccw(polygons[sitenbr].pointlist[i].coord, polygons[sitenbr].pointlist[j].coord, corners[c]))
						{
							any = 1;
						}
						else
						{
							cornerinpolygon[c] = 0;
						}
					}
				}
				if (!any) break;
			}
		}
		if (any)
		{
			for(c = 0; c < 4; c++)
			{
				if (cornerinpolygon[c])
				{
//					printf("adding corger (%lf,%lf) to %d\n", corners[c].x, corners[c].y, sitenbr);
					pushpoint(sitenbr, corners[c].x, corners[c].y, 0);
				}
			}
		}
		qsort(polygons[sitenbr].pointlist, polygons[sitenbr].numpoints, sizeof(PolygonPoint), anglecomp);

		polygons[sitenbr].boundary = 0;
	}

        *numpoints = polygons[sitenbr].numpoints;
        *pS = polygons[sitenbr].pointlist;
}


void VoronoiDiagramGenerator::clip_line(struct Edge *e)
{
	struct Site *s1, *s2, *ts1, *ts2;
	float x1=0,x2=0,y1=0,y2=0, temp = 0;
	int boundary1 = 0, boundary2 = 0;


	x1 = e->reg[0]->coord.x;
	x2 = e->reg[1]->coord.x;
	y1 = e->reg[0]->coord.y;
	y2 = e->reg[1]->coord.y;

        if(sqrt(((x2 - x1) * (x2 - x1)) + ((y2 - y1) * (y2 - y1))) == 0)
        {
                return;
        }

	pxmin = borderMinX;
	pxmax = borderMaxX;
	pymin = borderMinY;
	pymax = borderMaxY;

	if(e -> a == 1.0 && e ->b >= 0.0)
	{
		s1 = e -> ep[1];
		s2 = e -> ep[0];

                ts1 = e -> reg[1];
                ts2 = e -> reg[0];
	}
	else
	{
		s1 = e -> ep[0];
		s2 = e -> ep[1];

                ts1 = e -> reg[0];
                ts2 = e -> reg[1];

	};

	if(e -> a == 1.0)
	{
		if (	s1!=(struct Site *)NULL
			&& s1->coordout.y > pymin && s1->coordout.y < pymax
			&& s1->coordout.x > pxmin && s1->coordout.x < pxmax)
		{
			x1 = s1->coordout.x;
			y1 = s1->coordout.y;
		}
		else
		{
			boundary1 = 1;
			y1 = pymin;
			if (s1!=(struct Site *)NULL && s1->coord.y > pymin)
			{
				y1 = s1->coord.y;
			}
			if(y1>pymax)
			{
				y1 = pymax;
			}
			x1 = e -> c - e -> b * y1;
		}

		if (	s2!=(struct Site *)NULL
			&& s2->coordout.y > pymin && s2->coordout.y < pymax
			&& s2->coordout.x > pxmin && s2->coordout.x < pxmax)
		{
			x2 = s2->coordout.x;
			y2 = s2->coordout.y;
		}
		else
		{
			boundary2 = 1;
			y2 = pymax;
			if (s2!=(struct Site *)NULL && s2->coord.y < pymax)
				y2 = s2->coord.y;
			if(y2<pymin)
			{
				y2 = pymin;
			}
			x2 = (e->c) - (e->b) * y2;
		}

		if (((x1> pxmax) & (x2>pxmax)) | ((x1<pxmin)&(x2<pxmin)))
		{
			// Line completely outside clipbox
			//printf("\nClipLine jumping out(3), x1 = %f, pxmin = %f, pxmax = %f",x1,pxmin,pxmax);
			return;
		}
		if(x1 > pxmax)
		{
			x1 = pxmax;
			y1 = (e -> c - x1)/e -> b;
		}
		if(x1 < pxmin)
		{
			x1 = pxmin;
			y1 = (e -> c - x1)/e -> b;
		}
		if(x2 > pxmax)
		{
			x2 = pxmax;
			y2 = (e -> c - x2)/e -> b;
		}
		if(x2 < pxmin)
		{
			x2 = pxmin;
			y2 = (e -> c - x2)/e -> b;
		}
	}
	else
	{
		if (	s1!=(struct Site *)NULL
			&& s1->coordout.y > pymin && s1->coordout.y < pymax
			&& s1->coordout.x > pxmin && s1->coordout.x < pxmax)
		{
			x1 = s1->coordout.x;
			y1 = s1->coordout.y;
		}
		else
		{
			boundary1 = 1;
			x1 = pxmin;
			if (s1!=(struct Site *)NULL && s1->coord.x > pxmin)
				x1 = s1->coord.x;
			if(x1>pxmax) 
			{
				//printf("\nClipped (3) x1 = %f to %f",x1,pxmin);
				//return;
				x1 = pxmax;
			}
			y1 = e -> c - e -> a * x1;
		}

		if (	s2!=(struct Site *)NULL
			&& s2->coordout.y > pymin && s2->coordout.y < pymax
			&& s2->coordout.x > pxmin && s2->coordout.x < pxmax)
		{
			x2 = s2->coordout.x;
			y2 = s2->coordout.y;
		}
		else
		{
			boundary2 = 1;
			x2 = pxmax;
			if (s2!=(struct Site *)NULL && s2->coord.x < pxmax)
				x2 = s2->coord.x;
			if(x2<pxmin)
			{
				//printf("\nClipped (4) x2 = %f to %f",x2,pxmin);
				//return;
				x2 = pxmin;
			}
			y2 = e -> c - e -> a * x2;
		}

		if (((y1> pymax) & (y2>pymax)) | ((y1<pymin)&(y2<pymin)))
		{
			//printf("\nClipLine jumping out(6), y1 = %f, pymin = %f, pymax = %f",y2,pymin,pymax);
			return;
		}
		if(y1 > pymax)
		{	y1 = pymax; x1 = (e -> c - y1)/e -> a;};
		if(y1 < pymin)
		{	y1 = pymin; x1 = (e -> c - y1)/e -> a;};
		if(y2 > pymax)
		{	y2 = pymax; x2 = (e -> c - y2)/e -> a;};
		if(y2 < pymin)
		{	y2 = pymin; x2 = (e -> c - y2)/e -> a;};
	};

        if(sqrt(((x2 - x1) * (x2 - x1)) + ((y2 - y1) * (y2 - y1))) == 0)
	{
		return;
	}

        pushpoint(ts1->sitenbr, x1, y1, boundary1);
        pushpoint(ts2->sitenbr, x2, y2, boundary2);
        pushpoint(ts1->sitenbr, x2, y2, boundary2);
        pushpoint(ts2->sitenbr, x1, y1, boundary1);
}


/* implicit parameters: nsites, sqrt_nsites, xmin, xmax, ymin, ymax,
deltax, deltay (can all be estimates).
Performance suffers if they are wrong; better to make nsites,
deltax, and deltay too big than too small.  (?) */

bool VoronoiDiagramGenerator::voronoi(int triangulate)
{
	struct Site *newsite, *bot, *top, *temp, *p;
	struct Site *v;
	struct Point newintstar;
	int pm;
	struct Halfedge *lbnd, *rbnd, *llbnd, *rrbnd, *bisector;
	struct Edge *e, *e2, *e3;

	PQinitialize();
	bottomsite = nextone();
	out_site(bottomsite);
	bool retval = ELinitialize();

	if(!retval)
		return false;

	newsite = nextone();
	while(1)
	{

		if(!PQempty())
			newintstar = PQ_min();

		//if the lowest site has a smaller y value than the lowest vector intersection, process the site
		//otherwise process the vector intersection		

		if (newsite != (struct Site *)NULL 	&& (PQempty() || newsite -> coord.y < newintstar.y
			|| (newsite->coord.y == newintstar.y && newsite->coord.x < newintstar.x)))
		{/* new site is smallest - this is a site event*/
			out_site(newsite);						//output the site
			lbnd = ELleftbnd(&(newsite->coord));				//get the first HalfEdge to the LEFT of the new site
			rbnd = ELright(lbnd);						//get the first HalfEdge to the RIGHT of the new site
			bot = rightreg(lbnd);						//if this halfedge has no edge, , bot = bottom site (whatever that is)
			e = bisect(bot, newsite);					//create a new edge that bisects 
			bisector = HEcreate(e, le);					//create a new HalfEdge, setting its ELpm field to 0			
			ELinsert(lbnd, bisector);					//insert this new bisector edge between the left and right vectors in a linked list	

			if ((p = intersect(lbnd, bisector)) != (struct Site *) NULL) 	//if the new bisector intersects with the left edge, remove the left edge's vertex, and put in the new one
			{	
				PQdelete(lbnd);
				PQinsert(lbnd, p, dist(p,newsite));
			};
			lbnd = bisector;						
			bisector = HEcreate(e, re);					//create a new HalfEdge, setting its ELpm field to 1
			ELinsert(lbnd, bisector);					//insert the new HE to the right of the original bisector earlier in the IF stmt

			if ((p = intersect(bisector, rbnd)) != (struct Site *) NULL)	//if this new bisector intersects with the
			{
				PQinsert(bisector, p, dist(p,newsite));			//push the HE into the ordered linked list of vertices
			};
			newsite = nextone();
		}
		else if (!PQempty()) /* intersection is smallest - this is a vector event */
		{
			lbnd = PQextractmin();						//pop the HalfEdge with the lowest vector off the ordered list of vectors				
			llbnd = ELleft(lbnd);						//get the HalfEdge to the left of the above HE
			rbnd = ELright(lbnd);						//get the HalfEdge to the right of the above HE
			rrbnd = ELright(rbnd);						//get the HalfEdge to the right of the HE to the right of the lowest HE 
			bot = leftreg(lbnd);						//get the Site to the left of the left HE which it bisects
			top = rightreg(rbnd);						//get the Site to the right of the right HE which it bisects

			out_triple(bot, top, rightreg(lbnd));		//output the triple of sites, stating that a circle goes through them

			v = lbnd->vertex;						//get the vertex that caused this event
			makevertex(v);							//set the vertex number - couldn't do this earlier since we didn't know when it would be processed
			e2 = lbnd->ELedge;
			e3 = rbnd->ELedge;
			endpoint(lbnd->ELedge,lbnd->ELpm,v);	//set the endpoint of the left HalfEdge to be this vector
			endpoint(rbnd->ELedge,rbnd->ELpm,v);	//set the endpoint of the right HalfEdge to be this vector
			ELdelete(lbnd);							//mark the lowest HE for deletion - can't delete yet because there might be pointers to it in Hash Map	
			PQdelete(rbnd);							//remove all vertex events to do with the  right HE
			ELdelete(rbnd);							//mark the right HE for deletion - can't delete yet because there might be pointers to it in Hash Map	
			pm = le;								//set the pm variable to zero

			if (bot->coord.y > top->coord.y)		//if the site to the left of the event is higher than the Site
			{										//to the right of it, then swap them and set the 'pm' variable to 1
				temp = bot;
				bot = top;
				top = temp;
				pm = re;
			}
			e = bisect(bot, top);					//create an Edge (or line) that is between the two Sites. This creates
													//the formula of the line, and assigns a line number to it
			bisector = HEcreate(e, pm);				//create a HE from the Edge 'e', and make it point to that edge with its ELedge field
			ELinsert(llbnd, bisector);				//insert the new bisector to the right of the left HE
			endpoint(e, re-pm, v, e2, e3);					//set one endpoint to the new edge to be the vector point 'v'.
													//If the site to the left of this bisector is higher than the right
													//Site, then this endpoint is put in position 0; otherwise in pos 1
			deref(v);								//delete the vector 'v'

			//if left HE and the new bisector don't intersect, then delete the left HE, and reinsert it
			if((p = intersect(llbnd, bisector)) != (struct Site *) NULL)
			{
				PQdelete(llbnd);
				PQinsert(llbnd, p, dist(p,bot));
			};

			//if right HE and the new bisector don't intersect, then reinsert it
			if ((p = intersect(bisector, rrbnd)) != (struct Site *) NULL)
			{
				PQinsert(bisector, p, dist(p,bot));
			};
		}
		else break;
	};

	for(lbnd=ELright(ELleftend); lbnd != ELrightend; lbnd=ELright(lbnd))
	{
		e = lbnd -> ELedge;

		clip_line(e);
	};

	cleanup();

	return true;
}


int scomp(const void *p1,const void *p2)
{
	struct Point *s1 = (Point*)p1, *s2=(Point*)p2;
	if(s1 -> y < s2 -> y) return(-1);
	if(s1 -> y > s2 -> y) return(1);
	if(s1 -> x < s2 -> x) return(-1);
	if(s1 -> x > s2 -> x) return(1);
	return(0);
}

int spcomp(const void *p1,const void *p2)
{
	struct SourcePoint *s1 = (SourcePoint*)p1, *s2=(SourcePoint*)p2;
	if(s1 -> y < s2 -> y) return(-1);
	if(s1 -> y > s2 -> y) return(1);
	if(s1 -> x < s2 -> x) return(-1);
	if(s1 -> x > s2 -> x) return(1);
	return(0);
}

int anglecomp(const void * p1, const void * p2)
{
        PolygonPoint * s1 = (PolygonPoint *)p1 ;
        PolygonPoint * s2 = (PolygonPoint *)p2 ;

        if (s1->angle < s2->angle) {
                return (-1) ;
        }
        if (s1->angle > s2->angle) {
                return (1) ;
        }
        return (0) ;
}

/* return a single in-storage site */
struct Site * VoronoiDiagramGenerator::nextone()
{
	struct Site *s;
	if(siteidx < nsites)
	{
		s = &sites[siteidx];
		siteidx += 1;
		return(s);
	}
	else
		return( (struct Site *)NULL);
}

