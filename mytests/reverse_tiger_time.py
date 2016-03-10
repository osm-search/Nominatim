import numpy as np
import urllib2 as url
import time

def test(strUrl, iPoints):
    #define bounding box for test
    # sw: left-lower corner
    sw_lng= -100.815
    sw_lat= 46.789
    # ne right-top corner
    ne_lng= -100.717
    ne_lat= 46.84
    aXvalues = np.linspace(ne_lng, sw_lng, num=iPoints)
    aYvalues = np.linspace(sw_lat, ne_lat, num=iPoints)
    for x in aXvalues:
        for y in aYvalues:
            url.urlopen( strUrl % (y,x))

strUrlLine = "http://localhost/nominatim/reverse.php?format=json&lat=%f&lon=%f"
start_time_line=time.time()
test(strUrlLine, 10)
end_time_line=time.time()
strUrlOld = "http://localhost/nominatim_old/reverse.php?format=json&lat=%f&lon=%f"
start_time_old=time.time()
test(strUrlOld, 10)
end_time_old=time.time()
print("Line: --- %s seconds ---" % (end_time_line-start_time_line))
print("Old: --- %s seconds ---" % (end_time_old-start_time_old))

#tested on 9th March 2016: Line: 354 seconds, Old: 363 seconds (with iPoints=100 => 10.000 single points)
# Line: 3.586 sec, Old: 3.643 sec (witch iPoints=10 => 100 single points)
