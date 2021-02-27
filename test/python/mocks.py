"""
Custom mocks for testing.
"""


class MockParamCapture:
    """ Mock that records the parameters with which a function was called
        as well as the number of calls.
    """
    def __init__(self, retval=0):
        self.called = 0
        self.return_value = retval

    def __call__(self, *args, **kwargs):
        self.called += 1
        self.last_args = args
        self.last_kwargs = kwargs
        return self.return_value
