from nominatim_db.tools.special_phrases.sp_importer import SPImporter


# Testing Database Class Pair Retrival using Conftest.py and placex
def test_get_classtype_pair_data(placex_table, def_config, temp_db_conn):
    for _ in range(100):
        placex_table.add(cls='highway', typ='motorway')  # edge case 100

    for _ in range(99):
        placex_table.add(cls='amenity', typ='prison')  # edge case 99

    for _ in range(150):
        placex_table.add(cls='tourism', typ='hotel')

    importer = SPImporter(config=def_config, conn=temp_db_conn, sp_loader=None)

    result = importer.get_classtype_pairs(min=100)

    expected = {
        ("highway", "motorway"),
        ("tourism", "hotel")
    }

    assert result == expected, f"Expected {expected}, got {result}"


def test_get_classtype_pair_data_more(placex_table, def_config, temp_db_conn):
    for _ in range(99):
        placex_table.add(cls='emergency', typ='firehydrant')  # edge case 99, not included

    for _ in range(199):
        placex_table.add(cls='amenity', typ='prison')

    for _ in range(3478):
        placex_table.add(cls='tourism', typ='hotel')

    importer = SPImporter(config=def_config, conn=temp_db_conn, sp_loader=None)

    result = importer.get_classtype_pairs(min=100)

    expected = {
        ("amenity", "prison"),
        ("tourism", "hotel")
    }

    assert result == expected, f"Expected {expected}, got {result}"


def test_get_classtype_pair_data_default(placex_table, def_config, temp_db_conn):
    for _ in range(1):
        placex_table.add(cls='emergency', typ='firehydrant')

    for _ in range(199):
        placex_table.add(cls='amenity', typ='prison')

    for _ in range(3478):
        placex_table.add(cls='tourism', typ='hotel')

    importer = SPImporter(config=def_config, conn=temp_db_conn, sp_loader=None)

    result = importer.get_classtype_pairs()

    expected = {
        ("amenity", "prison"),
        ("tourism", "hotel"),
        ("emergency", "firehydrant")
    }

    assert result == expected, f"Expected {expected}, got {result}"
