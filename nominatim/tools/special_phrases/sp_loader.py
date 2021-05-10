"""
    Module containing the SPLoader class.
"""
from abc import ABC, abstractmethod

class SPLoader(ABC):
    """
        Base class for special phrases loaders.
        Handle the loading of special phrases from external sources.
    """
    def __iter__(self):
        return self

    @abstractmethod
    def __next__(self):
        pass
