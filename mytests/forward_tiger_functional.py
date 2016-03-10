import numpy as np
import urllib2 as url
import json as json
import random_points_bbox
import time

def test(num):
    #first get some random points in the bbox
    aPoints = random_points_bbox.getPoints(num, -100.815, 46.789, -100.717, 46.84)
    #get the addresses
    sReverseUrl = "http://localhost/nominatim/reverse.php?format=json&lat=%f&lon=%f"
    aAddresses = []
    for point in aPoints:
        response = url.urlopen(sReverseUrl % (point[1], point[0]))
        aAddresses.append(json.load(response)['address'])
    #print aAddresses
    # now we have all the addresses of the points in a list
    # lets forward geocode this list
    sOldUrl = "http://localhost/nominatim_old/search.php?format=json&city=%s&street=%s&addressdetails=1"
    sLineUrl = "http://localhost/nominatim/search.php?format=json&city=%s&street=%s&addressdetails=1"
    diff_lat =0
    diff_lon =0
    points =0
    for address in aAddresses:
        if 'house_number' in address and 'road' in address:
            responseOld = url.urlopen(sOldUrl % (address['city'], address['house_number']+' '+address['road']))
            dataOld = json.load(responseOld)
            print dataOld[0]['display_name']
            responseLine = url.urlopen(sLineUrl % (address['city'], address['house_number']+' '+address['road']))
            dataLine = json.load(responseLine)
            print dataLine[0]['display_name']
            temp_diff_lat = np.abs(float(dataOld[0]['lat'])-float(dataLine[0]['lat']))
            temp_diff_lon = np.abs(float(dataOld[0]['lon'])-float(dataLine[0]['lon']))
            print "diff lat: "+str(temp_diff_lat*111166)+", diff lon: "+str(temp_diff_lon*250456)
            diff_lat += temp_diff_lat
            diff_lon += temp_diff_lon
            points +=1

    print "Average difference in lat degrees with %d elements: %f (meters: %f)" % (points, diff_lat/points, diff_lat/points*111166)
    print "Average difference in lon degrees with %d elements: %f (meters: %f)" % (points, diff_lon/points, diff_lon/points*250456)
    # at 46.8 deg: 1 deg lat=111.166, 1 deg lon=250.456
        
test(20)
