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
from typing import Iterable
import csv
import os
from nominatim.tools.special_phrases.special_phrase import SpecialPhrase
from nominatim.errors import UsageError

class SPCsvLoader:
    """
        Handles loading of special phrases from external csv file.
    """
    def __init__(self, csv_path: str) -> None:
        self.csv_path = csv_path


    def generate_phrases(self) -> Iterable[SpecialPhrase]:
        """ Open and parse the given csv file.
            Create the corresponding SpecialPhrases.
        """
        self._check_csv_validity()

        with open(self.csv_path, encoding='utf-8') as fd:
            reader = csv.DictReader(fd, delimiter=',')
            for row in reader:
                yield SpecialPhrase(row['phrase'], row['class'], row['type'], row['operator'])


    def _check_csv_validity(self) -> None:
        """
            Check that the csv file has the right extension.
        """
        _, extension = os.path.splitext(self.csv_path)

        if extension != '.csv':
            raise UsageError(f'The file {self.csv_path} is not a csv file.')
