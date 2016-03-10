import numpy as np

def getPoints(num, sw_lng, sw_lat, ne_lng, ne_lat):
    aResult = np.empty(shape=(num,2))
    for i in range(0,num):
        aResult[i] = [np.random.uniform(ne_lng, sw_lng), np.random.uniform(sw_lat, ne_lat)]
    return aResult
