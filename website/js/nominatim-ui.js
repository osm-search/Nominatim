var map;
var last_click_latlng;

jQuery(document).on('ready', function(){
	$('#q').focus();

	map = new L.map('map', {
				center: [nominatim_map_init.lat, nominatim_map_init.lon],
				zoom:   nominatim_map_init.zoom,
				attributionControl: false,
				scrollWheelZoom:    false,
				touchZoom:          false,
			});

	L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
//		attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
	}).addTo(map);



	function display_map_position(mouse_lat_lng){

		html_mouse = "mouse position " + (mouse_lat_lng ? [mouse_lat_lng.lat.toFixed(5), mouse_lat_lng.lng.toFixed(5)].join(',') : '-');
		html_click = "last click: " + (last_click_latlng ? [last_click_latlng.lat.toFixed(5),last_click_latlng.lng.toFixed(5)].join(',') : '-');

		html_center = 
			"map center: " + 
			map.getCenter().lat.toFixed(5) + ',' + map.getCenter().lng.toFixed(5) +
			" <a target='_blank' href='" + map_link_to_osm() + "'>view on osm.org</a>";

		html_viewbox = "viewbox: " + map_viewbox_as_string();

		$('#map-position').html([html_center,html_viewbox,html_click,html_mouse].join('<br/>'));
		$('input#use_viewbox').trigger('change');
	}

	map.on('move', function(e) {
		display_map_position();
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
		$('input[name=viewbox]').val( $(this).prop('checked') ? map_viewbox_as_string() : '');
	});



	function map_viewbox_as_string() {
		// since .toBBoxString() doesn't round numbers
		return [
			map.getBounds().getSouthWest().lat.toFixed(5),
			map.getBounds().getSouthWest().lng.toFixed(5),
			map.getBounds().getNorthEast().lat.toFixed(5),
			map.getBounds().getNorthEast().lng.toFixed(5) ].join(',');
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
		return L.circleMarker([result.lat,result.lon], { radius: 50, weight: 1, fillColor: '#F0F7FF', color: 'red', opacity: 0.75});
	}

	var layerGroup = new L.layerGroup().addTo(map);
	function highlight_result(position, bool_focus){
		var result = nominatim_results[position];
		if (!result){ return }
		var result_el = get_result_element(position);

		$('.result').removeClass('highlight');
		result_el.addClass('highlight');

		layerGroup.clearLayers();

		if (result.aBoundingBox){

			console.log('bounding box, maybe polygon', result);
			var bounds = [[result.aBoundingBox[0]*1,result.aBoundingBox[2]*1], [result.aBoundingBox[1]*1,result.aBoundingBox[3]*1]];
			map.fitBounds(bounds);
			if (result.astext && result.astext.match(/POLY/) ){
				var layer = omnivore.wkt.parse(result.astext);
				layerGroup.addLayer(layer);
				// layer.addTo(map);
				// addedLayers.push(layer);
			}
			else {
				var layer = L.rectangle(bounds, {color: "#ff7800", weight: 1} );
				layerGroup.addLayer(layer);
			}
		}
		else {
			// console.log('lat,lon,zoom');
			map.panTo([result.lat,result.lon], result.zoom || nominatim_map_init.zoom);
			var circle = circle_for_result(result);
			circle.on('click', function(){
				highlight_result(i);
			});
			layerGroup.addLayer(layer);

			// circle.addTo(map);
		}

		var crosshairIcon = L.icon({
			iconUrl:     'images/crosshair.png',
			iconSize:    [12, 12],
			iconAnchor:  [6, 6],
		});
		var crossMarker = new L.Marker([result.lat,result.lon], { icon: crosshairIcon, clickable: false});
		layerGroup.addLayer(crossMarker);

		// crossMarker.addTo(map);
		// addedLayers.push(crossMarker);


		if (bool_focus){
			$('#map').focus();
		}
	}

	$.each(nominatim_results, function(i, result){

	});


	$('.result').on('click', function(e){
		highlight_result($(this).data('position'), true);
	});

	highlight_result(0, false);


});
