<?php
# These settings control the import of special phrases from the wiki.

# Languages to download the special phrases for.
$aLanguageIn = array(
			'af',
			'ar',
			'br',
			'ca',
			'cs',
			'de',
			'en',
			'es',
			'et',
			'eu',
			'fa',
			'fi',
			'fr',
			'gl',
			'hr',
			'hu',
			'ia',
			'is',
			'it',
			'ja',
			'mk',
			'nl',
			'no',
			'pl',
			'ps',
			'pt',
			'ru',
			'sk',
			'sv',
			'uk',
			'vi',
		);

# class/type combinations to exclude
$aTagsBlacklist = array(
	'boundary' => array('administrative'),
	'place' => array('house', 'houses'),
);
# If a class is in the white list then all types will 
# be ignored except the ones given in the list.
# Also use this list to exclude an entire class from
# special phrases.
$aTagsWhitelist = array(
	'highway' => array('bus_stop', 'rest_area', 'raceway'),
	'building' => array(),
);
