from nominatim.data.place_info import PlaceInfo
from nominatim.data.place_name import PlaceName
from nominatim.tokenizer.place_sanitizer import PlaceSanitizer
from typing import Mapping, Optional, List
import pytest

class TestTagJapanese:
    @pytest.fixture(autouse=True)
    def setup_country(self, def_config):
        self.config = def_config

    def run_sanitizer_on(self,type, **kwargs):
        place = PlaceInfo({
            'address': kwargs,
            'country_code': 'ja'
        })
        sanitizer_args = {'step': 'tag-japanese'}
        _, address = PlaceSanitizer([sanitizer_args], self.config).process_names(place)
        tmp_list = [(p.name,p.kind) for p in address]
        return sorted(tmp_list)

    def test_on_address(self):
        res = self.run_sanitizer_on('address', name='foo', ref='bar', ref_abc='baz')
        assert res == [('bar','ref'),('baz','ref_abc'),('foo','name')]

    def test_housenumber_type(self):
        res = self.run_sanitizer_on('address', housenumber='2', block_number='6')
        assert res == [('6-2','housenumber')]

