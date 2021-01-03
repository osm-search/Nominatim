"""
Collection of assertion functions used for the steps.
"""

class Almost:

    def __init__(self, value, offset=0.00001):
        self.value = value
        self.offset = offset

    def __eq__(self, other):
        return abs(other - self.value) < self.offset
