# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
    Module containing the SPCsvLoader class.

    The class allows to load phrases from a csv file.
"""
import csv
import os
from collections.abc import Iterator
from nominatim.tools.special_phrases.special_phrase import SpecialPhrase
from nominatim.errors import UsageError

class SPCsvLoader(Iterator):
    """
        Handles loading of special phrases from external csv file.
    """
    def __init__(self, csv_path):
        super().__init__()
        self.csv_path = csv_path
        self.has_been_read = False

    def __next__(self):
        if self.has_been_read:
            raise StopIteration()

        self.has_been_read = True
        self.check_csv_validity()
        return self.parse_csv()

    def parse_csv(self):
        """
            Open and parse the given csv file.
            Create the corresponding SpecialPhrases.
        """
        phrases = set()

        with open(self.csv_path) as file:
            reader = csv.DictReader(file, delimiter=',')
            for row in reader:
                phrases.add(
                    SpecialPhrase(row['phrase'], row['class'], row['type'], row['operator'])
                )
        return phrases

    def check_csv_validity(self):
        """
            Check that the csv file has the right extension.
        """
        _, extension = os.path.splitext(self.csv_path)

        if extension != '.csv':
            raise UsageError(f'The file {self.csv_path} is not a csv file.')
