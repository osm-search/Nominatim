# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
    Contains the class which handles statistics for the
    import of special phrases.
"""
import logging
LOG = logging.getLogger()

class SpecialPhrasesImporterStatistics():
    # pylint: disable-msg=too-many-instance-attributes
    """
        Class handling statistics of the import
        process of special phrases.
    """
    def __init__(self):
        self._intialize_values()

    def _intialize_values(self):
        """
            Set all counts for the global
            import to 0.
        """
        self.tables_created = 0
        self.tables_deleted = 0
        self.tables_ignored = 0
        self.invalids = 0

    def notify_one_phrase_invalid(self):
        """
            Add +1 to the count of invalid entries
            fetched from the wiki.
        """
        self.invalids += 1

    def notify_one_table_created(self):
        """
            Add +1 to the count of created tables.
        """
        self.tables_created += 1

    def notify_one_table_deleted(self):
        """
            Add +1 to the count of deleted tables.
        """
        self.tables_deleted += 1

    def notify_one_table_ignored(self):
        """
            Add +1 to the count of ignored tables.
        """
        self.tables_ignored += 1

    def notify_import_done(self):
        """
            Print stats for the whole import process
            and reset all values.
        """
        LOG.info('====================================================================')
        LOG.info('Final statistics of the import:')
        LOG.info('- %s phrases were invalid.', self.invalids)
        if self.invalids > 0:
            LOG.info('  Those invalid phrases have been skipped.')
        LOG.info('- %s tables were ignored as they already exist on the database',
                 self.tables_ignored)
        LOG.info('- %s tables were created', self.tables_created)
        LOG.info('- %s tables were deleted from the database', self.tables_deleted)
        if self.tables_deleted > 0:
            LOG.info('  They were deleted as they are not valid anymore.')

        if self.invalids > 0:
            LOG.warning('%s phrases were invalid and have been skipped during the whole process.',
                        self.invalids)

        self._intialize_values()
