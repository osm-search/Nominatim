# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helpers for progress logging.
"""
import logging
from datetime import datetime

LOG = logging.getLogger()

INITIAL_PROGRESS = 10

class ProgressLogger:
    """ Tracks and prints progress for the indexing process.
        `name` is the name of the indexing step being tracked.
        `total` sets up the total number of items that need processing.
        `log_interval` denotes the interval in seconds at which progress
        should be reported.
    """

    def __init__(self, name: str, total: int, log_interval: int = 1) -> None:
        self.name = name
        self.total_places = total
        self.done_places = 0
        self.rank_start_time = datetime.now()
        self.log_interval = log_interval
        self.next_info = INITIAL_PROGRESS if LOG.isEnabledFor(logging.WARNING) else total + 1

    def add(self, num: int = 1) -> None:
        """ Mark `num` places as processed. Print a log message if the
            logging is at least info and the log interval has passed.
        """
        self.done_places += num

        if self.done_places < self.next_info:
            return

        now = datetime.now()
        done_time = (now - self.rank_start_time).total_seconds()

        if done_time < 2:
            self.next_info = self.done_places + INITIAL_PROGRESS
            return

        places_per_sec = self.done_places / done_time
        eta = (self.total_places - self.done_places) / places_per_sec

        LOG.warning("Done %d in %d @ %.3f per second - %s ETA (seconds): %.2f",
                    self.done_places, int(done_time),
                    places_per_sec, self.name, eta)

        self.next_info += int(places_per_sec) * self.log_interval

    def done(self) -> None:
        """ Print final statistics about the progress.
        """
        rank_end_time = datetime.now()

        if rank_end_time == self.rank_start_time:
            diff_seconds = 0.0
            places_per_sec = float(self.done_places)
        else:
            diff_seconds = (rank_end_time - self.rank_start_time).total_seconds()
            places_per_sec = self.done_places / diff_seconds

        LOG.warning("Done %d/%d in %d @ %.3f per second - FINISHED %s\n",
                    self.done_places, self.total_places, int(diff_seconds),
                    places_per_sec, self.name)
