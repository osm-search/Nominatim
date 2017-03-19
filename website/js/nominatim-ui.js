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

jQuery(document).on('ready', function(){

    if ( !$('#search-page,#reverse-page').length ){ return; }
    
    var is_reverse_search = !!( $('#reverse-page').length );

    $('#q').focus();

    map = new L.map('map', {
                attributionControl: (nominatim_map_init.tile_attribution && nominatim_map_init.tile_attribution.length),
                scrollWheelZoom:    !L.Browser.touch,
                touchZoom:          false
            });

    L.tileLayer(nominatim_map_init.tile_url, {
        noWrap: true, // otherwise we end up with click coordinates like latitude -728
        // moved to footer
        attribution: (nominatim_map_init.tile_attribution || null ) //'&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    map.setView([nominatim_map_init.lat, nominatim_map_init.lon], nominatim_map_init.zoom);

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

        html_mouse = "mouse position " + (mouse_lat_lng ? [mouse_lat_lng.lat.toFixed(5), mouse_lat_lng.lng.toFixed(5)].join(',') : '-');
        html_click = "last click: " + (last_click_latlng ? [last_click_latlng.lat.toFixed(5),last_click_latlng.lng.toFixed(5)].join(',') : '-');

        html_center = 
            "map center: " + 
            map.getCenter().lat.toFixed(5) + ',' + map.getCenter().lng.toFixed(5) +
            " <a target='_blank' href='" + map_link_to_osm() + "'>view on osm.org</a>";

        html_zoom = "map zoom: " + map.getZoom();

        html_viewbox = "viewbox: " + map_viewbox_as_string();

        $('#map-position-inner').html([html_center,html_zoom,html_viewbox,html_click,html_mouse].join('<br/>'));

        var reverse_params = {
            lat: map.getCenter().lat.toFixed(5),
            lon: map.getCenter().lng.toFixed(5),
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
        // since .toBBoxString() doesn't round numbers
        return [
            map.getBounds().getSouthWest().lng.toFixed(5), // left
            map.getBounds().getNorthEast().lat.toFixed(5), // top
            map.getBounds().getNorthEast().lng.toFixed(5), // right
            map.getBounds().getSouthWest().lat.toFixed(5)  // bottom
        ].join(',');
    }
    function map_link_to_osm(){
        return "http://openstreetmap.org/#map=" + map.getZoom() + "/" + map.getCenter().lat + "/" + map.getCenter().lng;
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
            if ( is_reverse_search ){
                // make sure the search coordinates are in the map view as well
                map.fitBounds([[result.lat,result.lon], [nominatim_map_init.lat,nominatim_map_init.lon]], {padding: [50,50], maxZoom: map.getZoom()});

                // better, but causes a leaflet warning
                // map.panInsideBounds([[result.lat,result.lon], [nominatim_map_init.lat,nominatim_map_init.lon]], {animate: false});
            }
            else {
                map.panTo([result.lat,result.lon], result.zoom || nominatim_map_init.zoom);
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
            $('form input[name=lon]').val( e.latlng.lng);
            $('form').submit();
        });

        $('#switch-coords').on('click', function(e){
            var lat = $('form input[name=lat]').val();
            var lon = $('form input[name=lon]').val();
            $('form input[name=lat]').val(lon);
            $('form input[name=lon]').val(lat);
            $('form').submit();
        });
    }

    highlight_result(0, false);


});


jQuery(document).on('ready', function(){

    if ( !$('#details-page').length ){ return; }


        map = new L.map('map', {
                    // center: [nominatim_map_init.lat, nominatim_map_init.lon],
                    // zoom:   nominatim_map_init.zoom,
                    attributionControl: (nominatim_map_init.tile_attribution && nominatim_map_init.tile_attribution.length),
                    scrollWheelZoom:    false,
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



});

