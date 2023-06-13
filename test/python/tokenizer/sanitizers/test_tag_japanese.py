import pytest


from nominatim.data.place_info import PlaceInfo
from nominatim.tokenizer.place_sanitizer import PlaceSanitizer


class TestTagJapanese:

    @pytest.fixture(autouse=True)
    def setup_country(self, def_config):
        self.config = def_config

    def run_sanitizer_on(self, type, **kwargs):
        place = PlaceInfo({
            'address': [
                PlaceName(kind='housenumber', name=kwargs.get('housenumber')),
                PlaceName(kind='block_number', name=kwargs.get('block_number')),
                PlaceName(kind='neighbourhood', name=kwargs.get('neighbourhood')),
            ],
            'country_code': 'ja'
        })

        sanitizer_args = {'step': 'tag-japanese'}

        _, address = PlaceSanitizer([sanitizer_args], self.config).process_names(place)

        return sorted([(p.kind, p.name) for p in address])

    def test_on_address(self):
        res = self.run_sanitizer_on(name='foo', ref='bar', ref_abc='baz')
        assert res == [('bar', 'ref'), ('baz', 'ref', 'abc'), ('foo', 'name')]

    def test_tag_without_housenumber_and_blocknumber(self):
        obj = PlaceInfo()
        obj.address = [
            PlaceName(kind='neighbourhood', name='2丁目')
        ]
        self.run_sanitizer_on(obj)

        assert [(p.kind, p.name) for p in obj.address] == [('place', '2丁目')]

    def test_housenumber_type(self):
        res = self.run_sanitizer_on(housenumber='2', block_number='6')
        assert res == [('housenumber', '6-2')]
