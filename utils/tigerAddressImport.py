#!/usr/bin/python
# Tiger road data to OSM conversion script
# Creates Karlsruhe-style address ways beside the main way
# based on the Massachusetts GIS script by christopher schmidt

#BUGS:
# On very tight curves, a loop may be generated in the address way.
# It would be nice if the ends of the address ways were not pulled back from dead ends


# Ways that include these mtfccs should not be uploaded
# H1100 Connector
# H3010 Stream/River
# H3013 Braided Stream
# H3020 Canal, Ditch or Aqueduct
# L4130 Point-to-Point Line
# L4140 Property/Parcel Line (Including PLSS)
# P0001 Nonvisible Linear Legal/Statistical Boundary
# P0002 Perennial Shoreline
# P0003 Intermittent Shoreline
# P0004 Other non-visible bounding Edge (e.g., Census water boundary, boundary of an areal feature)
ignoremtfcc = [ "H1100", "H3010", "H3013", "H3020", "L4130", "L4140", "P0001", "P0002", "P0003", "P0004" ]

# Sets the distance that the address ways should be from the main way, in feet.
address_distance = 30

# Sets the distance that the ends of the address ways should be pulled back from the ends of the main way, in feet
address_pullback = 45

import sys, os.path, json
try:
    from osgeo import ogr
    from osgeo import osr
except:
    import ogr
    import osr

# https://www.census.gov/geo/reference/codes/cou.html 
# tiger_county_fips.json was generated from the following:
# wget https://www2.census.gov/geo/docs/reference/codes/files/national_county.txt
# cat national_county.txt | perl -F, -naE'($F[0] ne 'AS') && $F[3] =~ s/ ((city|City|County|District|Borough|City and Borough|Municipio|Municipality|Parish|Island|Census Area)(?:, |\Z))+//; say qq(  "$F[1]$F[2]": "$F[3], $F[0]",)'
json_fh = open(os.path.dirname(sys.argv[0]) + "/tiger_county_fips.json")
county_fips_data = json.load(json_fh)

def parse_shp_for_geom_and_tags( filename ):
    #ogr.RegisterAll()

    dr = ogr.GetDriverByName("ESRI Shapefile")
    poDS = dr.Open( filename )

    if poDS == None:
        raise "Open failed."

    poLayer = poDS.GetLayer( 0 )

    fieldNameList = []
    layerDefinition = poLayer.GetLayerDefn()
    for i in range(layerDefinition.GetFieldCount()):
        fieldNameList.append(layerDefinition.GetFieldDefn(i).GetName())
    # sys.stderr.write(",".join(fieldNameList))

    poLayer.ResetReading()

    ret = []

    poFeature = poLayer.GetNextFeature()
    while poFeature:
        tags = {}
        
        # WAY ID
        tags["tiger:way_id"] = int( poFeature.GetField("TLID") )
        
        # FEATURE IDENTIFICATION
        mtfcc = poFeature.GetField("MTFCC");
        if mtfcc != None:

            if mtfcc == "L4010":        #Pipeline
                tags["man_made"] = "pipeline"
            if mtfcc == "L4020":        #Powerline
                tags["power"] = "line"
            if mtfcc == "L4031":        #Aerial Tramway/Ski Lift
                tags["aerialway"] = "cable_car"
            if mtfcc == "L4110":        #Fence Line
                tags["barrier"] = "fence"
            if mtfcc == "L4125":        #Cliff/Escarpment
                tags["natural"] = "cliff"
            if mtfcc == "L4165":        #Ferry Crossing
                tags["route"] = "ferry"
            if mtfcc == "R1011":        #Railroad Feature (Main, Spur, or Yard)
                tags["railway"] = "rail"
                ttyp = poFeature.GetField("TTYP")
                if ttyp != None:
                    if ttyp == "S":
                        tags["service"] = "spur"
                    if ttyp == "Y":
                        tags["service"] = "yard"
                    tags["tiger:ttyp"] = ttyp
            if mtfcc == "R1051":        #Carline, Streetcar Track, Monorail, Other Mass Transit Rail)
                tags["railway"] = "light_rail"
            if mtfcc == "R1052":        #Cog Rail Line, Incline Rail Line, Tram
                tags["railway"] = "incline"
            if mtfcc == "S1100":
                tags["highway"] = "primary"
            if mtfcc == "S1200":
                tags["highway"] = "secondary"
            if mtfcc == "S1400":
                tags["highway"] = "residential"
            if mtfcc == "S1500":
                tags["highway"] = "track"
            if mtfcc == "S1630":        #Ramp
                tags["highway"] = "motorway_link"
            if mtfcc == "S1640":        #Service Drive usually along a limited access highway
                tags["highway"] = "service"
            if mtfcc == "S1710":        #Walkway/Pedestrian Trail
                tags["highway"] = "path"
            if mtfcc == "S1720":
                tags["highway"] = "steps"
            if mtfcc == "S1730":        #Alley
                tags["highway"] = "service"
                tags["service"] = "alley"
            if mtfcc == "S1740":        #Private Road for service vehicles (logging, oil, fields, ranches, etc.)
                tags["highway"] = "service"
                tags["access"] = "private"
            if mtfcc == "S1750":        #Private Driveway
                tags["highway"] = "service"
                tags["access"] = "private"
                tags["service"] = "driveway"
            if mtfcc == "S1780":        #Parking Lot Road
                tags["highway"] = "service"
                tags["service"] = "parking_aisle"
            if mtfcc == "S1820":        #Bike Path or Trail
                tags["highway"] = "cycleway"
            if mtfcc == "S1830":        #Bridle Path
                tags["highway"] = "bridleway"
            tags["tiger:mtfcc"] = mtfcc

        # FEATURE NAME
        if poFeature.GetField("FULLNAME"):
            #capitalizes the first letter of each word
            name = poFeature.GetField( "FULLNAME" )
            tags["name"] = name

            #Attempt to guess highway grade
            if name[0:2] == "I-":
                tags["highway"] = "motorway"
            if name[0:3] == "US ":
                tags["highway"] = "primary"
            if name[0:3] == "US-":
                tags["highway"] = "primary"
            if name[0:3] == "Hwy":
                if tags["highway"] != "primary":
                    tags["highway"] = "secondary"

        # TIGER 2017 no longer contains this field
        if 'DIVROAD' in fieldNameList:
            divroad = poFeature.GetField("DIVROAD")
            if divroad != None:
                if divroad == "Y" and "highway" in tags and tags["highway"] == "residential":
                    tags["highway"] = "tertiary"
                tags["tiger:separated"] = divroad

        statefp = poFeature.GetField("STATEFP")
        countyfp = poFeature.GetField("COUNTYFP")
        if (statefp != None) and (countyfp != None):
            county_name = county_fips_data.get(statefp + '' + countyfp)
            if county_name:
                tags["tiger:county"] = county_name.encode("utf-8")

        # tlid = poFeature.GetField("TLID")
        # if tlid != None:
        #     tags["tiger:tlid"] = tlid

        lfromadd = poFeature.GetField("LFROMADD")
        if lfromadd != None:
            tags["tiger:lfromadd"] = lfromadd

        rfromadd = poFeature.GetField("RFROMADD")
        if rfromadd != None:
            tags["tiger:rfromadd"] = rfromadd

        ltoadd = poFeature.GetField("LTOADD")
        if ltoadd != None:
            tags["tiger:ltoadd"] = ltoadd

        rtoadd = poFeature.GetField("RTOADD")
        if rtoadd != None:
            tags["tiger:rtoadd"] = rtoadd

        zipl = poFeature.GetField("ZIPL")
        if zipl != None:
            tags["tiger:zip_left"] = zipl

        zipr = poFeature.GetField("ZIPR")
        if zipr != None:
            tags["tiger:zip_right"] = zipr

        if mtfcc not in ignoremtfcc:
            # COPY DOWN THE GEOMETRY
            geom = []
            
            rawgeom = poFeature.GetGeometryRef()
            for i in range( rawgeom.GetPointCount() ):
                geom.append( (rawgeom.GetX(i), rawgeom.GetY(i)) )
    
            ret.append( (geom, tags) )
        poFeature = poLayer.GetNextFeature()
        
    return ret


# ====================================
# to do read .prj file for this data
# Change the Projcs_wkt to match your datas prj file.
# ====================================
projcs_wkt = \
"""GEOGCS["GCS_North_American_1983",
        DATUM["D_North_American_1983",
        SPHEROID["GRS_1980",6378137,298.257222101]],
        PRIMEM["Greenwich",0],
        UNIT["Degree",0.017453292519943295]]"""

from_proj = osr.SpatialReference()
from_proj.ImportFromWkt( projcs_wkt )

# output to WGS84
to_proj = osr.SpatialReference()
to_proj.SetWellKnownGeogCS( "EPSG:4326" )

tr = osr.CoordinateTransformation( from_proj, to_proj )

import math
def length(segment, nodelist):
    '''Returns the length (in feet) of a segment'''
    first = True
    distance = 0
    lat_feet = 364613  #The approximate number of feet in one degree of latitude
    for point in segment:
        pointid, (lat, lon) = nodelist[ round_point( point ) ]
        if first:
            first = False
        else:
            #The approximate number of feet in one degree of longitute
            lrad = math.radians(lat)
            lon_feet = 365527.822 * math.cos(lrad) - 306.75853 * math.cos(3 * lrad) + 0.3937 * math.cos(5 * lrad)
            distance += math.sqrt(((lat - previous[0])*lat_feet)**2 + ((lon - previous[1])*lon_feet)**2)
        previous = (lat, lon)
    return distance

def addressways(waylist, nodelist, first_id):
    id = first_id
    lat_feet = 364613  #The approximate number of feet in one degree of latitude
    distance = float(address_distance)
    ret = []

    for waykey, segments in waylist.items():
        waykey = dict(waykey)
        rsegments = []
        lsegments = []
        for segment in segments:
            lsegment = []
            rsegment = []
            lastpoint = None

            # Don't pull back the ends of very short ways too much
            seglength = length(segment, nodelist)
            if seglength < float(address_pullback) * 3.0:
                pullback = seglength / 3.0
            else:
                pullback = float(address_pullback)
            if "tiger:lfromadd" in waykey:
                lfromadd = waykey["tiger:lfromadd"]
            else:
                lfromadd = None
            if "tiger:ltoadd" in waykey:
                ltoadd = waykey["tiger:ltoadd"]
            else:
                ltoadd = None
            if "tiger:rfromadd" in waykey:
                rfromadd = waykey["tiger:rfromadd"]
            else: 
                rfromadd = None
            if "tiger:rtoadd" in waykey:
                rtoadd = waykey["tiger:rtoadd"]
            else:
                rtoadd = None
            if rfromadd != None and rtoadd != None:
                right = True
            else:
                right = False
            if lfromadd != None and ltoadd != None:
                left = True
            else:
                left = False
            if left or right:
                first = True
                firstpointid, firstpoint = nodelist[ round_point( segment[0] ) ]

                finalpointid, finalpoint = nodelist[ round_point( segment[len(segment) - 1] ) ]
                for point in segment:
                    pointid, (lat, lon) = nodelist[ round_point( point ) ]

                    #The approximate number of feet in one degree of longitute
                    lrad = math.radians(lat)
                    lon_feet = 365527.822 * math.cos(lrad) - 306.75853 * math.cos(3 * lrad) + 0.3937 * math.cos(5 * lrad)

#Calculate the points of the offset ways
                    if lastpoint != None:
                        #Skip points too close to start
                        if math.sqrt((lat * lat_feet - firstpoint[0] * lat_feet)**2 + (lon * lon_feet - firstpoint[1] * lon_feet)**2) < pullback:
                            #Preserve very short ways (but will be rendered backwards)
                            if pointid != finalpointid:
                                continue
                        #Skip points too close to end
                        if math.sqrt((lat * lat_feet - finalpoint[0] * lat_feet)**2 + (lon * lon_feet - finalpoint[1] * lon_feet)**2) < pullback:
                            #Preserve very short ways (but will be rendered backwards)
                            if (pointid != firstpointid) and (pointid != finalpointid):
                                continue

                        X = (lon - lastpoint[1]) * lon_feet
                        Y = (lat - lastpoint[0]) * lat_feet
                        if Y != 0:
                            theta = math.pi/2 - math.atan( X / Y)
                            Xp = math.sin(theta) * distance
                            Yp = math.cos(theta) * distance
                        else:
                            Xp = 0
                            if X > 0:
                                Yp = -distance
                            else:
                                Yp = distance

                        if Y > 0:
                            Xp = -Xp
                        else:
                            Yp = -Yp
                                
                        if first:
                            first = False
                            dX =  - (Yp * (pullback / distance)) / lon_feet #Pull back the first point
                            dY = (Xp * (pullback / distance)) / lat_feet
                            if left:
                                lpoint = (lastpoint[0] + (Yp / lat_feet) - dY, lastpoint[1] + (Xp / lon_feet) - dX)
                                lsegment.append( (id, lpoint) )
                                id += 1
                            if right:
                                rpoint = (lastpoint[0] - (Yp / lat_feet) - dY, lastpoint[1] - (Xp / lon_feet) - dX)
                                rsegment.append( (id, rpoint) )
                                id += 1

                        else:
                            #round the curves
                            if delta[1] != 0:
                                theta = abs(math.atan(delta[0] / delta[1]))
                            else:
                                theta = math.pi / 2
                            if Xp != 0:
                                theta = theta - abs(math.atan(Yp / Xp))
                            else: theta = theta - math.pi / 2
                            r = 1 + abs(math.tan(theta/2))
                            if left:
                                lpoint = (lastpoint[0] + (Yp + delta[0]) * r / (lat_feet * 2), lastpoint[1] + (Xp + delta[1]) * r / (lon_feet * 2))
                                lsegment.append( (id, lpoint) )
                                id += 1
                            if right:
                                rpoint = (lastpoint[0] - (Yp + delta[0]) * r / (lat_feet * 2), lastpoint[1] - (Xp + delta[1]) * r / (lon_feet * 2))
                                
                                rsegment.append( (id, rpoint) )
                                id += 1

                        delta = (Yp, Xp)

                    lastpoint = (lat, lon)


#Add in the last node
                dX =  - (Yp * (pullback / distance)) / lon_feet
                dY = (Xp * (pullback / distance)) / lat_feet
                if left:
                    lpoint = (lastpoint[0] + (Yp + delta[0]) / (lat_feet * 2) + dY, lastpoint[1] + (Xp + delta[1]) / (lon_feet * 2) + dX )
                    lsegment.append( (id, lpoint) )
                    id += 1
                if right:
                    rpoint = (lastpoint[0] - Yp / lat_feet + dY, lastpoint[1] - Xp / lon_feet + dX)
                    rsegment.append( (id, rpoint) )
                    id += 1

#Generate the tags for ways and nodes
                zipr = ''
                zipl = ''
                name = ''
                county = ''
                if "tiger:zip_right" in waykey:
                    zipr = waykey["tiger:zip_right"]
                if "tiger:zip_left" in waykey:
                    zipl = waykey["tiger:zip_left"]
                if "name" in waykey:
                    name = waykey["name"]
                if "tiger:county" in waykey:
                    county = waykey["tiger:county"]
                if "tiger:separated" in waykey: # No longer set in Tiger-2017
                    separated = waykey["tiger:separated"]
                else:
                    separated = "N"

#Write the nodes of the offset ways
                if right:
                    rlinestring = [];
                    for i, point in rsegment:
                        rlinestring.append( "%f %f" % (point[1], point[0]) )
                if left:
                    llinestring = [];
                    for i, point in lsegment:
                        llinestring.append( "%f %f" % (point[1], point[0]) )
                if right:
                    rsegments.append( rsegment )
                if left:
                    lsegments.append( lsegment )
                rtofromint = right        #Do the addresses convert to integers?
                ltofromint = left        #Do the addresses convert to integers?
                if right:
                    try: rfromint = int(rfromadd)
                    except:
                        print("Non integer address: %s" % rfromadd)
                        rtofromint = False
                    try: rtoint = int(rtoadd)
                    except:
                        print("Non integer address: %s" % rtoadd)
                        rtofromint = False
                if left:
                    try: lfromint = int(lfromadd)
                    except:
                        print("Non integer address: %s" % lfromadd)
                        ltofromint = False
                    try: ltoint = int(ltoadd)
                    except:
                        print("Non integer address: %s" % ltoadd)
                        ltofromint = False
                if right:
                    id += 1

                    interpolationtype = "all";
                    if rtofromint:
                        if (rfromint % 2) == 0 and (rtoint % 2) == 0:
                            if separated == "Y":        #Doesn't matter if there is another side
                                interpolationtype = "even";
                            elif ltofromint and (lfromint % 2) == 1 and (ltoint % 2) == 1:
                                interpolationtype = "even";
                        elif (rfromint % 2) == 1 and (rtoint % 2) == 1:
                            if separated == "Y":        #Doesn't matter if there is another side
                                interpolationtype = "odd";
                            elif ltofromint and (lfromint % 2) == 0 and (ltoint % 2) == 0:
                                interpolationtype = "odd";

                    ret.append( "SELECT tiger_line_import(ST_GeomFromText('LINESTRING(%s)',4326), %s, %s, %s, %s, %s, %s);" %
                                ( ",".join(rlinestring), sql_quote(rfromadd), sql_quote(rtoadd), sql_quote(interpolationtype), sql_quote(name), sql_quote(county), sql_quote(zipr) ) )

                if left:
                    id += 1

                    interpolationtype = "all";
                    if ltofromint:
                        if (lfromint % 2) == 0 and (ltoint % 2) == 0:
                            if separated == "Y":
                                interpolationtype = "even";
                            elif rtofromint and (rfromint % 2) == 1 and (rtoint % 2) == 1:
                                interpolationtype = "even";
                        elif (lfromint % 2) == 1 and (ltoint % 2) == 1:
                            if separated == "Y":
                                interpolationtype = "odd";
                            elif rtofromint and (rfromint %2 ) == 0 and (rtoint % 2) == 0:
                                interpolationtype = "odd";

                    ret.append( "SELECT tiger_line_import(ST_GeomFromText('LINESTRING(%s)',4326), %s, %s, %s, %s, %s, %s);" %
                                ( ",".join(llinestring), sql_quote(lfromadd), sql_quote(ltoadd), sql_quote(interpolationtype), sql_quote(name), sql_quote(county), sql_quote(zipl) ) )

    return ret

def sql_quote( string ):
    return "'" + string.replace("'", "''") + "'"

def unproject( point ):
    pt = tr.TransformPoint( point[0], point[1] )
    return (pt[1], pt[0])

def round_point( point, accuracy=8 ):
    return tuple( [ round(x,accuracy) for x in point ] )

def compile_nodelist( parsed_gisdata, first_id=1 ):
    nodelist = {}
    
    i = first_id
    for geom, tags in parsed_gisdata:
        if len( geom )==0:
            continue
        
        for point in geom:
            r_point = round_point( point )
            if r_point not in nodelist:
                nodelist[ r_point ] = (i, unproject( point ))
                i += 1
            
    return (i, nodelist)

def adjacent( left, right ):
    left_left = round_point(left[0])
    left_right = round_point(left[-1])
    right_left = round_point(right[0])
    right_right = round_point(right[-1])
    
    return ( left_left == right_left or
             left_left == right_right or
             left_right == right_left or
             left_right == right_right )
             
def glom( left, right ):
    left = list( left )
    right = list( right )
    
    left_left = round_point(left[0])
    left_right = round_point(left[-1])
    right_left = round_point(right[0])
    right_right = round_point(right[-1])
    
    if left_left == right_left:
        left.reverse()
        return left[0:-1] + right
        
    if left_left == right_right:
        return right[0:-1] + left
        
    if left_right == right_left:
        return left[0:-1] + right
        
    if left_right == right_right:
        right.reverse()
        return left[0:-1] + right
        
    raise 'segments are not adjacent'

def glom_once( segments ):
    if len(segments)==0:
        return segments
    
    unsorted = list( segments )
    x = unsorted.pop(0)
    
    while len( unsorted ) > 0:
        n = len( unsorted )
        
        for i in range(0, n):
            y = unsorted[i]
            if adjacent( x, y ):
                y = unsorted.pop(i)
                x = glom( x, y )
                break
                
        # Sorted and unsorted lists have no adjacent segments
        if len( unsorted ) == n:
            break
            
    return x, unsorted
    
def glom_all( segments ):
    unsorted = segments
    chunks = []
    
    while unsorted != []:
        chunk, unsorted = glom_once( unsorted )
        chunks.append( chunk )
        
    return chunks
        
                

def compile_waylist( parsed_gisdata ):
    waylist = {}
    
    #Group by tiger:way_id
    for geom, tags in parsed_gisdata:
        way_key = tags.copy()
        way_key = ( way_key['tiger:way_id'], tuple( [(k,v) for k,v in way_key.items()] ) )
        
        if way_key not in waylist:
            waylist[way_key] = []
            
        waylist[way_key].append( geom )
    
    ret = {}
    for (way_id, way_key), segments in waylist.items():
        ret[way_key] = glom_all( segments )
    return ret
            

def shape_to_sql( shp_filename, sql_filename ):
    
    print("parsing shpfile %s" % shp_filename)
    parsed_features = parse_shp_for_geom_and_tags( shp_filename )
    
    print("compiling nodelist")
    i, nodelist = compile_nodelist( parsed_features )
    
    print("compiling waylist")
    waylist = compile_waylist( parsed_features )

    print("preparing address ways")
    sql_lines = addressways(waylist, nodelist, i)

    print("writing %s" % sql_filename)
    fp = open( sql_filename, "w" )
    fp.write( "\n".join( sql_lines ) )
    fp.close()
    
if __name__ == '__main__':
    import sys, os.path
    if len(sys.argv) < 3:
        print("%s input.shp output.sql" % sys.argv[0])
        sys.exit()
    shp_filename = sys.argv[1]
    sql_filename = sys.argv[2]
    shape_to_sql(shp_filename, sql_filename)
