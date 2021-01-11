"""
Collection of assertion functions used for the steps.
"""

class Almost:
    """ Compares a float value with a certain jitter.
    """
    def __init__(self, value, offset=0.00001):
        self.value = value
        self.offset = offset

    def __eq__(self, other):
        return abs(other - self.value) < self.offset

class Bbox:
    """ Comparator for bounding boxes.
    """
    def __init__(self, bbox_string):
        self.coord = [float(x) for x in bbox_string.split(',')]

    def __contains__(self, item):
        if isinstance(item, str):
            item = item.split(',')
        item = list(map(float, item))

        if len(item) == 2:
            return self.coord[0] <= item[0] <= self.coord[2] \
                   and self.coord[1] <= item[1] <= self.coord[3]

        if len(item) == 4:
            return item[0] >= self.coord[0] and item[1] <= self.coord[1] \
                   and item[2] >= self.coord[2] and item[3] <= self.coord[3]

        raise ValueError("Not a coordinate or bbox.")

    def __str__(self):
        return str(self.coord)
