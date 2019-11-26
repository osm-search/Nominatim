var map;
var last_click_latlng;

function parse_and_normalize_geojson_string(raw_string){
    // normalize places the geometry into a featurecollection, similar to
    // https://github.com/mapbox/geojson-normalize
    var parsed_geojson = {
        type: "FeatureCollection",
        features: [
            {
                type: "Feature",
                geometry: JSON.parse(raw_string),
                properties: {}
            }
        ]
    };
    return parsed_geojson;
}

jQuery(document).ready(function(){

    if ( !$('#search-page,#reverse-page').length ){ return; }
    
    var is_reverse_search = !!( $('#reverse-page').length );

    $('#q').focus();

    map = new L.map('map', {
                attributionControl: (nominatim_map_init.tile_attribution && nominatim_map_init.tile_attribution.length),
                scrollWheelZoom:    true, // !L.Browser.touch,
                touchZoom:          false
            });

    L.tileLayer(nominatim_map_init.tile_url, {
        // moved to footer
        attribution: (nominatim_map_init.tile_attribution || null ) //'&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    map.setView([nominatim_map_init.lat, nominatim_map_init.lon], nominatim_map_init.zoom);

    var osm2 = new L.TileLayer(nominatim_map_init.tile_url, {minZoom: 0, maxZoom: 13, attribution: (nominatim_map_init.tile_attribution || null )});
    var miniMap = new L.Control.MiniMap(osm2, {toggleDisplay: true}).addTo(map);

    if ( is_reverse_search ){
        // We don't need a marker, but an L.circle instance changes radius once you zoom in/out
        var cm = L.circleMarker([nominatim_map_init.lat,nominatim_map_init.lon], { radius: 5, weight: 2, fillColor: '#ff7800', color: 'red', opacity: 0.75, clickable: false});
        cm.addTo(map);
    }

    var MapPositionControl = L.Control.extend({
            options: {
                    position: 'topright'
            },

            onAdd: function (map) {
                    var container = L.DomUtil.create('div', 'my-custom-control');

                    $(container).text('show map bounds').addClass('leaflet-bar btn btn-sm btn-default').on('click', function(e){
                        e.preventDefault();
                        e.stopPropagation();
                        $('#map-position').show();
                        $(container).hide();
                    });
                    $('#map-position-close a').on('click', function(e){
                        e.preventDefault();
                        e.stopPropagation();
                        $('#map-position').hide();
                        $(container).show();
                    });

                    return container;
            }
    });

    map.addControl(new MapPositionControl());


    function display_map_position(mouse_lat_lng){

        if (mouse_lat_lng) {
            mouse_lat_lng = map.wrapLatLng(mouse_lat_lng);
        }
        html_mouse = "mouse position " + (mouse_lat_lng ? [mouse_lat_lng.lat.toFixed(5), mouse_lat_lng.lng.toFixed(5)].join(',') : '-');
        html_click = "last click: " + (last_click_latlng ? [last_click_latlng.lat.toFixed(5),last_click_latlng.lng.toFixed(5)].join(',') : '-');

        html_center = 
            "map center: " + 
            map.getCenter().lat.toFixed(5) + ',' + map.getCenter().lng.toFixed(5) +
            " <a target='_blank' href='" + map_link_to_osm() + "'>view on osm.org</a>";

        html_zoom = "map zoom: " + map.getZoom();

        html_viewbox = "viewbox: " + map_viewbox_as_string();

        $('#map-position-inner').html([html_center,html_zoom,html_viewbox,html_click,html_mouse].join('<br/>'));

        var center_lat_lng = map.wrapLatLng(map.getCenter());
        var reverse_params = {
            lat: center_lat_lng.lat.toFixed(5),
            lon: center_lat_lng.lng.toFixed(5),
            zoom: map.getZoom(),
            format: 'html'
        }
        $('#switch-to-reverse').attr('href', 'reverse.php?' + $.param(reverse_params));

        $('input#use_viewbox').trigger('change');
    }

    function update_viewbox_field(){
        // hidden HTML field
        $('input[name=viewbox]').val( $('input#use_viewbox').prop('checked') ? map_viewbox_as_string() : '');
    }

    map.on('move', function(e) {
        display_map_position();
        update_viewbox_field();
    });

    map.on('mousemove', function(e) {
        display_map_position(e.latlng);
    });

    map.on('click', function(e) {
        last_click_latlng = e.latlng;
        display_map_position();
    });

    map.on('load', function(e){
        display_map_position();
    });


    $('input#use_viewbox').on('change', function(){
        update_viewbox_field();
    });



    function map_viewbox_as_string() {
        var bounds = map.getBounds();
        var west = bounds.getWest();
        var east = bounds.getEast();

        if ((east - west) >= 360) { // covers more than whole planet
            west = map.getCenter().lng-179.999;
            east = map.getCenter().lng+179.999;
        }
        east = L.latLng(77, east).wrap().lng;
        west = L.latLng(77, west).wrap().lng;

        return [
            west.toFixed(5), // left
            bounds.getNorth().toFixed(5), // top
            east.toFixed(5), // right
            bounds.getSouth().toFixed(5) // bottom
        ].join(',');
    }
    function map_link_to_osm(){
        return "https://openstreetmap.org/#map=" + map.getZoom() + "/" + map.getCenter().lat + "/" + map.getCenter().lng;
    }

    function get_result_element(position){
        return $('.result').eq(position);
    }
    function marker_for_result(result){
        return L.marker([result.lat,result.lon], {riseOnHover:true,title:result.name });
    }
    function circle_for_result(result){
        return L.circleMarker([result.lat,result.lon], { radius: 10, weight: 2, fillColor: '#ff7800', color: 'blue', opacity: 0.75, clickable: !is_reverse_search});
    }

    var layerGroup = new L.layerGroup().addTo(map);
    function highlight_result(position, bool_focus){
        var result = nominatim_results[position];
        if (!result){ return }
        var result_el = get_result_element(position);

        $('.result').removeClass('highlight');
        result_el.addClass('highlight');

        layerGroup.clearLayers();

        if (result.lat){
            var circle = circle_for_result(result);
            circle.on('click', function(){
                highlight_result(position);
            });
            layerGroup.addLayer(circle);            
        }
        if (result.aBoundingBox){

            var bounds = [[result.aBoundingBox[0]*1,result.aBoundingBox[2]*1], [result.aBoundingBox[1]*1,result.aBoundingBox[3]*1]];
            map.fitBounds(bounds);

            if (result.asgeojson && result.asgeojson.match(/(Polygon)|(Line)/) ){

                var geojson_layer = L.geoJson(
                    parse_and_normalize_geojson_string(result.asgeojson),
                    {
                        // http://leafletjs.com/reference-1.0.3.html#path-option
                        style: function(feature) {
                            return { interactive: false, color: 'blue' }; 
                        }
                    }
                );
                layerGroup.addLayer(geojson_layer);
            }
            else {
                // var layer = L.rectangle(bounds, {color: "#ff7800", weight: 1} );
                // layerGroup.addLayer(layer);
            }
        }
        else {
            var result_coord = L.latLng(result.lat, result.lon);
            if ( result_coord ){
                if ( is_reverse_search ){
                    // make sure the search coordinates are in the map view as well
                    map.fitBounds([result_coord, [nominatim_map_init.lat,nominatim_map_init.lon]], {padding: [50,50], maxZoom: map.getZoom()});

                    // better, but causes a leaflet warning
                    // map.panInsideBounds([[result.lat,result.lon], [nominatim_map_init.lat,nominatim_map_init.lon]], {animate: false});
                }
                else {
                    map.panTo(result_coord, result.zoom || nominatim_map_init.zoom);
                }
            }
        }

        // var crosshairIcon = L.icon({
        //  iconUrl:     'images/crosshair.png',
        //  iconSize:    [12, 12],
        //  iconAnchor:  [6, 6],
        // });
        // var crossMarker = new L.Marker([result.lat,result.lon], { icon: crosshairIcon, clickable: false});
        // layerGroup.addLayer(crossMarker);



        if (bool_focus){
            $('#map').focus();
        }
    }


    $('.result').on('click', function(e){
        highlight_result($(this).data('position'), true);
    });

    if ( is_reverse_search ){
        map.on('click', function(e){
            $('form input[name=lat]').val( e.latlng.lat);
            $('form input[name=lon]').val( e.latlng.wrap().lng);
            $('form').submit();
        });

        $('#switch-coords').on('click', function(e){
            e.preventDefault();
            e.stopPropagation();
            var lat = $('form input[name=lat]').val();
            var lon = $('form input[name=lon]').val();
            $('form input[name=lat]').val(lon);
            $('form input[name=lon]').val(lat);
            $('form').submit();
        });
    } else {
        var search_params = new URLSearchParams(location.search);
        var viewbox = search_params.get('viewbox');
        if (viewbox) {
            var coords = viewbox.split(','); // <x1>,<y1>,<x2>,<y2>
            var bounds = L.latLngBounds([coords[1], coords[0]], [coords[3], coords[2]]);
            L.rectangle(bounds, {color: "#69d53e", weight: 3, dashArray: '5 5', opacity: 0.8, fill: false}).addTo(map);
        }
    }

    highlight_result(0, false);

    // common mistake is to copy&paste latitude and longitude into the 'lat' search box
    $('form input[name=lat]').on('change', function(){
        var coords = $(this).val().split(',');
        if (coords.length == 2) {
            $(this).val(L.Util.trim(coords[0]));
            $(this).siblings('input[name=lon]').val(L.Util.trim(coords[1]));
        }
    });

});


jQuery(document).ready(function(){

    if ( !$('#details-index-page').length ){ return; }

    $('#form-by-type-and-id,#form-by-osm-url').on('submit', function(e){
        e.preventDefault();

        var val = $(this).find('input[type=edit]').val();
        var matches = val.match(/^\s*([NWR])(\d+)\s*$/i);

        if (!matches) {
            matches = val.match(/\/(relation|way|node)\/(\d+)\s*$/);
        }

        if (matches) {
            $(this).find('input[name=osmtype]').val(matches[1].charAt(0).toUpperCase());
            $(this).find('input[name=osmid]').val(matches[2]);
            $(this).get(0).submit();
        } else {
            alert('invalid input');
        }
    });
});

jQuery(document).ready(function(){

    if ( !$('#details-page').length ){ return; }


        map = new L.map('map', {
                    // center: [nominatim_map_init.lat, nominatim_map_init.lon],
                    // zoom:   nominatim_map_init.zoom,
                    attributionControl: (nominatim_map_init.tile_attribution && nominatim_map_init.tile_attribution.length),
                    scrollWheelZoom:    true, // !L.Browser.touch,
                    touchZoom:          false,
                });


        L.tileLayer(nominatim_map_init.tile_url, {
            // moved to footer
            attribution: (nominatim_map_init.tile_attribution || null ) //'&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        var layerGroup = new L.layerGroup().addTo(map);

        var circle = L.circleMarker([nominatim_result.lat,nominatim_result.lon], { radius: 10, weight: 2, fillColor: '#ff7800', color: 'blue', opacity: 0.75});
        map.addLayer(circle);

        if ( nominatim_result.asgeojson ){

            var geojson_layer = L.geoJson(
                parse_and_normalize_geojson_string(nominatim_result.asgeojson),
                {
                    // http://leafletjs.com/reference-1.0.3.html#path-option
                    style: function(feature) {
                        return { interactive: false, color: 'blue' }; 
                    }
                }
            );
            map.addLayer(geojson_layer);
            map.fitBounds(geojson_layer.getBounds());
        } else {
            map.setView([nominatim_result.lat,nominatim_result.lon],10);
        }

        var osm2 = new L.TileLayer(nominatim_map_init.tile_url, {minZoom: 0, maxZoom: 13, attribution: (nominatim_map_init.tile_attribution || null )});
        var miniMap = new L.Control.MiniMap(osm2, {toggleDisplay: true}).addTo(map);


});

