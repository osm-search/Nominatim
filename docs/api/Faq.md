# Frequently Asked Questions

## API Results

#### 1. The address of my search results contains far-away places that don't belong there.

Nominatim computes the address from two sources in the OpenStreetMap data:
from administrative boundaries and from place nodes. Boundaries are the more
useful source. They precisely describe an area. So it is very clear for
Nominatim if a point belongs to an area or not. Place nodes are more complicated.
These are only points without any precise extent. So Nominatim has to take a
guess and assume that an address belongs to the closest place node it can find.
In an ideal world, Nominatim would not need the place nodes but there are
many places on earth where there are no precise boundaries available for
all parts that make up an address. This is in particular true for the more
local address parts, like villages and suburbs. Therefore it is not possible
to completely dismiss place nodes. And sometimes they sneak in where they
don't belong.

As a OpenStreetMap mapper, you can improve the situation in two ways: if you
see a place node for which already an administrative area exists, then you
should _link_ the two by adding the node with a 'label' role to the boundary
relation. If there is no administrative area, you can add the approximate
extent of the place and tag it place=<something> as well.

#### 2. When doing reverse search, the address details have parts that don't contain the point I was looking up.

There is a common misconception how the reverse API call works in Nominatim.
Reverse does not give you the address of the point you asked for. Reverse
returns the closest object to the point you asked for and then returns the
address of that object. Now, if you are close to a border, then the closest
object may be across that border. When Nominatim then returns the address,
it contains the county/state/country across the border.

#### 3. I get different counties/states/countries when I change the zoom parameter in the reverse query. How is that possible?

This is basically the same problem as in the previous answer.
The zoom level influences at which [search rank](https://wiki.openstreetmap.org/wiki/Nominatim/Development_overview#Country_to_street_level) Nominatim starts looking
for the closest object. So the closest house number maybe on one side of the
border while the closest street is on the other. As the address details contain
the address of the closest object found, you might sometimes get one result,
sometimes the other for the closest point.

#### 4. Can you return the continent?

Nominatim assigns each map feature one country. Those outside any administrative
boundaries are assigned a special no-country. Continents or other super-national
administrations (e.g. European Union, NATO, Custom unions) are not supported,
see also [Administrative Boundary](https://wiki.openstreetmap.org/wiki/Tag:boundary%3Dadministrative#Super-national_administrations).

#### 5. Can you return the timezone?

See this separate OpenStreetMap-based project [Timezone Boundary Builder](https://github.com/evansiroky/timezone-boundary-builder).

#### 6. I want to download a list of streets/restaurants of a city/region

The [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) is more
suited for these kinds of queries.

That said if you installed your own Nominatim instance you can use the
`/utils/export.php` PHP script as basis to return such lists.
