import numpy as np
import urllib2 as url
import json as json
import random_points_bbox
import time

def test(num):
    #first get some random points in the bbox
    aPoints = random_points_bbox.getPoints(num, -100.815, 46.789, -100.717, 46.84)
    #get the addresses
    sReverseUrl = "http://localhost/nominatim_old/reverse.php?format=json&lat=%f&lon=%f"
    aAddresses = []
    for point in aPoints:
        response = url.urlopen(sReverseUrl % (point[1], point[0]))
        aAddresses.append(json.load(response)['address'])
    #print aAddresses
    # now we have all the addresses of the points in a list
    # lets forward geocode this list
    sOldUrl = "http://localhost/nominatim_old/search.php?format=json&city=%s&street=%s&addressdetails=1"
    sLineUrl = "http://localhost/nominatim/search.php?format=json&city=%s&street=%s&addressdetails=1"
    start_old = time.time()
    for address in aAddresses:
        if 'house_number' in address and 'road' in address:
            responseOld = url.urlopen(sOldUrl % (address['city'], address['house_number']+' '+address['road']))
            #dataOld = json.load(responseOld)
            #print dataOld[0]['display_name']
        elif 'road' in address:
            responseOld = url.urlopen(sOldUrl % (address['city'], address['road']))
            #dataOld = json.load(responseOld)
            #print dataOld[0]['display_name']
    end_old = time.time()        
    for address in aAddresses:
        if 'house_number' in address and 'road' in address:
            responseLine = url.urlopen(sLineUrl % (address['city'], address['house_number']+' '+address['road']))
        elif 'road' in address:
            responseLine = url.urlopen(sLineUrl % (address['city'], address['road']))
    end_line = time.time()
    
    print "Seconds old search for %d elements: %f" % (num,end_old-start_old)
    print "Seconds line search for %d elements: %f" % (num,end_line-end_old)
    
        
test(100)
# 100 points: old: 7.11 sec, new: 7.47 sec
# 1000 points: old: 65.69 sec, new: 66.96 sec
