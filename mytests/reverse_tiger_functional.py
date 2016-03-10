import numpy as np
import urllib2 as url
import json as json
import random_points_bbox

def test_compare(strUrl1, strUrl2, iPoints):
    #define bounding box for test
    # sw: left-lower corner
    sw_lng= -100.815
    sw_lat= 46.789
    # ne right-top corner
    ne_lng= -100.717
    ne_lat= 46.84
    #first get some random points in the bbox
    aPoints = random_points_bbox.getPoints(iPoints, -100.815, 46.789, -100.717, 46.84)
    same = 0
    differ = 0
    differ_street=0
    missing_housenumber_1=0
    missing_housenumber_2=0
    for point in aPoints:
        response = url.urlopen( strUrl1 % (point[1],point[0]))
        data1 = json.load(response)
        response = url.urlopen(strUrl2 % (point[1],point[0]))
        data2 = json.load(response)
        if data1['address'] == data2['address']:
            same+=1
        elif 'road' in data1['address'] and 'road' in data2['address']:
            differ+=1
            print 'different: '+str(data1['address'])+' - ' + str(data2['address'])
            if data1['address']['road'] != data2['address']['road']:
                differ_street +=1
        if 'house_number' not in data1['address']:
            missing_housenumber_1 +=1
            print 'missing housenumber in Line: '+str(data1['address'])
        if 'house_number' not in data2['address']:
            missing_housenumber_2 +=1
            print 'missing housenumber in Old: '+str(data2['address'])
            
            
    print 'Number of same values: '+str(same)
    print 'Number of different values: '+str(differ)
    print 'Number of different streets: '+str(differ_street)
    print 'Points without housenumber in Line: '+str(missing_housenumber_1)
    print 'Points without housenumber in Old: '+str(missing_housenumber_2)
strUrlLine = "http://localhost/nominatim/reverse.php?format=json&lat=%f&lon=%f"
strUrlOld = "http://localhost/nominatim_old/reverse.php?format=json&lat=%f&lon=%f"

test_compare(strUrlLine,strUrlOld, 100)
