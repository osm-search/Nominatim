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
            'country_code': 'jp'
        })
        sanitizer_args = {'step': 'tag-japanese'}
        _, address = PlaceSanitizer([sanitizer_args], self.config).process_names(place)
        tmp_list = [(p.name,p.kind) for p in address]
        return sorted(tmp_list)

    def test_on_address(self):
        res = self.run_sanitizer_on('address', name='foo', ref='bar', ref_abc='baz')
        assert res == [('bar','ref'),('baz','ref_abc'),('foo','name')]

    def test_housenumber(self):
        res = self.run_sanitizer_on('address', housenumber='2')
        assert res == [('2','housenumber')]

    def test_blocknumber(self):
        res = self.run_sanitizer_on('address', block_number='6')
        assert res == [('6','housenumber')]

    #def test_neighbourhood(self):
    #    res = self.run_sanitizer_on('address',neighbourhood='8丁目')
    #    assert res == [('8','place')]
    def test_neighbourhood(self):
        res = self.run_sanitizer_on('address', neighbourhood='8')
        assert res == [('8','place')]
    def test_quarter(self):
        res = self.run_sanitizer_on('address', quarter='kase')
        assert res==[('kase','place')]

    def test_housenumber_blocknumber(self):
        res = self.run_sanitizer_on('address', housenumber='2', block_number='6')
        assert res == [('6-2','housenumber')]

    def test_housenumber_blocknumber(self):
        res = self.run_sanitizer_on('address', housenumber='2', neighbourhood='8')
        assert res == [('2','housenumber'),('8','place')]

    def test_housenumber_blocknumber(self):
        res = self.run_sanitizer_on('address', block_number='6', neighbourhood='8')
        assert res == [('6','housenumber'),('8','place')]

    def test_housenumber_blocknumber_neighbourhood(self):
        res = self.run_sanitizer_on('address', housenumber='2', block_number='6', neighbourhood='8')
        assert res == [('6-2','housenumber'),('8','place')]

    def test_housenumber_blocknumber_neighbourhood_quarter(self):
        res = self.run_sanitizer_on('address', housenumber='2', block_number='6', neighbourhood='8',quarter='kase')
        assert res == [('6-2','housenumber'),('kase-8','place')]
    def test_neighbourhood_quarter(self):
        res = self.run_sanitizer_on('address', neighbourhood='8',quarter='kase')
        assert res == [('kase-8','place')] 
