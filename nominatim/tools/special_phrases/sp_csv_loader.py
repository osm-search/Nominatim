"""
    Module containing the SPCsvLoader class.

    The class allows to load phrases from a csv file.
"""
import csv
import os
from nominatim.tools.special_phrases.special_phrase import SpecialPhrase
from nominatim.tools.special_phrases.sp_loader import SPLoader
from nominatim.errors import UsageError

class SPCsvLoader(SPLoader):
    """
        Base class for special phrases loaders.
        Handle the loading of special phrases from external sources.
    """
    def __init__(self, csv_path):
        super().__init__()
        self.csv_path = csv_path
        self.has_been_read = False

    def __next__(self):
        if self.has_been_read:
            raise StopIteration()

        self.has_been_read = True
        SPCsvLoader.check_csv_validity(self.csv_path)
        return SPCsvLoader.parse_csv(self.csv_path)

    @staticmethod
    def parse_csv(csv_path):
        """
            Open and parse the given csv file.
            Create the corresponding SpecialPhrases.
        """
        phrases = set()

        with open(csv_path) as file:
            reader = csv.DictReader(file, delimiter=',')
            for row in reader:
                phrases.add(
                    SpecialPhrase(row['phrase'], row['class'], row['type'], row['operator'])
                )
        return phrases

    @staticmethod
    def check_csv_validity(csv_path):
        """
            Check that the csv file has the right extension.
        """
        _, extension = os.path.splitext(csv_path)

        if extension != '.csv':
            raise UsageError('The file {} is not a csv file.'.format(csv_path))
