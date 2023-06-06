import pytest


from nominatim.data.place_info import PlaceInfo
from nominatim.tokenizer.place_sanitizer import PlaceSanitizer


class TestTagJapanese:

    @pytest.fixture(autouse=True)
    def setup_country(self, def_config):
        self.config = def_config

    def run_sanitizer_on(self, type, **kwargs):

        place = PlaceInfo({type: {k.replace('_', ':'): v for k, v in kwargs.items()},
                            'country_code': 'ja'})

        sanitizer_args = {'step': 'tag-japanese'}

        name, address = PlaceSanitizer([sanitizer_args],
                                    self.config).process_names(place)

        return {
                'name': sorted([(p.name, p.kind, p.suffix or '') for p in name]),
                'address': sorted([(p.name, p.kind, p.suffix or '') for p in address])
            }


    def test_on_name(self):
        res = self.run_sanitizer_on('name', name='foo', ref='bar', ref_abc='baz')

        assert res.get('name') == []

    def test_on_address(self):
        res = self.run_sanitizer_on('address', name='foo', ref='bar', ref_abc='baz')

        assert res.get('address') == [('bar', 'ref', ''), ('baz', 'ref', 'abc'),
                                        ('foo', 'name', '')]
