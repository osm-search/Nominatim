import pytest
import tempfile
import os

from nominatim_db.tools.special_phrases.sp_importer import SPImporter

# Testing Database Class Pair Retrival using Mock Database
def test_get_classtype_pairs(monkeypatch):
    class Config:
        def load_sub_configuration(self, path, section=None):
            return {"blackList": {}, "whiteList": {}}

    class Cursor:
        def execute(self, query): pass
        def fetchall(self):
            return [
                ("highway", "motorway"),  
                ("historic", "castle")    
            ]
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass

    class Connection:
        def cursor(self): return Cursor()

    config = Config()
    conn = Connection()
    importer = SPImporter(config=config, conn=conn, sp_loader=None)

    result = importer.get_classtype_pairs()

    expected = {
        ("highway", "motorway"),
        ("historic", "castle")
    }

    assert result == expected

# Testing Database Class Pair Retrival using Conftest.py and placex
def test_get_classtype_pair_data(placex_table, temp_db_conn):
    class Config:
        def load_sub_configuration(self, *_):
            return {'blackList': {}, 'whiteList': {}}
        
    for _ in range(101):
        placex_table.add(cls='highway', typ='motorway') # edge case 101

    for _ in range(99):
        placex_table.add(cls='amenity', typ='prison') # edge case 99

    for _ in range(150):
        placex_table.add(cls='tourism', typ='hotel')

    config = Config()
    importer = SPImporter(config=config, conn=temp_db_conn, sp_loader=None)

    result = importer.get_classtype_pairs()

    expected = {
        ("highway", "motorway"),
        ("tourism", "hotel")
    }

    assert result == expected, f"Expected {expected}, got {result}"

def test_get_classtype_pair_data_more(placex_table, temp_db_conn):
    class Config:
        def load_sub_configuration(self, *_):
            return {'blackList': {}, 'whiteList': {}}
        
    for _ in range(100):
        placex_table.add(cls='emergency', typ='firehydrant') # edge case 100, not included

    for _ in range(199):
        placex_table.add(cls='amenity', typ='prison') 

    for _ in range(3478):
        placex_table.add(cls='tourism', typ='hotel')

    config = Config()
    importer = SPImporter(config=config, conn=temp_db_conn, sp_loader=None)

    result = importer.get_classtype_pairs()

    expected = {
        ("amenity", "prison"),
        ("tourism", "hotel")
    }

    assert result == expected, f"Expected {expected}, got {result}"
