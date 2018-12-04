<?php
    // Script to extract structured city and street data
    // from a running nominatim instance as CSV data


    require_once(CONST_BasePath.'/lib/init-cmd.php');
    require_once(CONST_BasePath.'/lib/ParameterParser.php');
    ini_set('memory_limit', '800M');

    $aCMDOptions = array(
                    'Export addresses as CSV file from a Nominatim database',
                    array('help', 'h', 0, 1, 0, 0, false, 'Show Help'),
                    array('quiet', 'q', 0, 1, 0, 0, 'bool', 'Quiet output'),
                    array('verbose', 'v', 0, 1, 0, 0, 'bool', 'Verbose output'),

                    array('output-type', '', 0, 1, 1, 1, 'str', 'Type of places to output (see below)'),
                    array('output-format', '', 0, 1, 1, 1, 'str', 'Column mapping (see below)'),
                    array('output-all-postcodes', '', 0, 1, 0, 0, 'bool', 'List all postcodes for address instead of just the most likely one'),
                    array('language', '', 0, 1, 1, 1, 'str', 'Preferred language for output (local name, if omitted)'),
                    array('restrict-to-country', '', 0, 1, 1, 1, 'str', 'Export only objects within country (country code)'),
                    array('restrict-to-osm-node', '', 0, 1, 1, 1, 'int', 'Export only objects that are children of this OSM node'),
                    array('restrict-to-osm-way', '', 0, 1, 1, 1, 'int', 'Export only objects that are children of this OSM way'),
                    array('restrict-to-osm-relation', '', 0, 1, 1, 1, 'int', 'Export only objects that are children of this OSM relation'),
                    "\nAddress ranks: continent, country, state, county, city, suburb, street, path",
                    'Additional output types: postcode, placeid (placeid for each object)',
                    "\noutput-format must be a semicolon-separated list of address ranks. Multiple ranks",
                    'can be merged into one column by simply using a comma-separated list.',
                    "\nDefault output-type: street",
        'Default output format: street;suburb;city;county;state;country'
                   );
    getCmdOpt($_SERVER['argv'], $aCMDOptions, $aCMDResult, true, true);

    $aRankmap = array(
                 'continent' => 1,
                 'country' => 4,
                 'state' => 8,
                 'county' => 12,
                 'city' => 16,
                 'suburb' => 20,
                 'street' => 26,
                 'path' => 27
                );

    $oDB =& getDB();

    if (isset($aCMDResult['output-type'])) {
        if (!isset($aRankmap[$aCMDResult['output-type']])) fail('unknown output-type: '.$aCMDResult['output-type']);
        $iOutputRank = $aRankmap[$aCMDResult['output-type']];
    } else {
        $iOutputRank = $aRankmap['street'];
    }


    // Preferred language
    $oParams = new Nominatim\ParameterParser();
    if (!isset($aCMDResult['language'])) $aCMDResult['language'] = 'xx';
    $aLangPrefOrder = $oParams->getPreferredLanguages($aCMDResult['language']);
    $sLanguagePrefArraySQL = 'ARRAY['.join(',', array_map('getDBQuoted', $aLangPrefOrder)).']';

    // output formatting: build up a lookup table that maps address ranks to columns
    $aColumnMapping = array();
    $iNumCol = 0;
    if (!isset($aCMDResult['output-format'])) $aCMDResult['output-format'] = 'street;suburb;city;county;state;country';
    foreach (preg_split('/\s*;\s*/', $aCMDResult['output-format']) as $sColumn) {
        $bHasData = false;
        foreach (preg_split('/\s*,\s*/', $sColumn) as $sRank) {
            if ($sRank == 'postcode' || $sRank == 'placeid') {
                $aColumnMapping[$sRank] = $iNumCol;
                $bHasData = true;
            } elseif (isset($aRankmap[$sRank])) {
                $iRank = $aRankmap[$sRank];
                if ($iRank <= $iOutputRank) {
                    $aColumnMapping[(string)$iRank] = $iNumCol;
                    $bHasData = true;
                }
            }
        }
        if ($bHasData) $iNumCol++;
    }

    // build the query for objects
    $sPlacexSQL = 'select min(place_id) as place_id, ';
    $sPlacexSQL .= 'array_agg(place_id) as place_ids, ';
    $sPlacexSQL .= 'country_code as cc, ';
    $sPlacexSQL .= 'postcode, ';
    // get the address places excluding postcodes
    $sPlacexSQL .= 'array(select address_place_id from place_addressline a';
    $sPlacexSQL .= ' where a.place_id = placex.place_id and isaddress';
    $sPlacexSQL .= '  and address_place_id != placex.place_id';
    $sPlacexSQL .= '  and not cached_rank_address in (5,11)';
    $sPlacexSQL .= '  and cached_rank_address > 2 order by cached_rank_address)';
    $sPlacexSQL .= ' as address';
    $sPlacexSQL .= ' from placex where name is not null and linked_place_id is null';

    $sPlacexSQL .= ' and rank_address = '.$iOutputRank;

    if (isset($aCMDResult['restrict-to-country'])) {
        $sPlacexSQL .= ' and country_code = '.getDBQuoted($aCMDResult['restrict-to-country']);
    }

    // restriction to parent place id
    $sParentId = false;
    $sOsmType = false;

    if (isset($aCMDResult['restrict-to-osm-node'])) {
        $sOsmType = 'N';
        $sOsmId = $aCMDResult['restrict-to-osm-node'];
    }
    if (isset($aCMDResult['restrict-to-osm-way'])) {
        $sOsmType = 'W';
        $sOsmId = $aCMDResult['restrict-to-osm-way'];
    }
    if (isset($aCMDResult['restrict-to-osm-relation'])) {
        $sOsmType = 'R';
        $sOsmId = $aCMDResult['restrict-to-osm-relation'];
    }
    if ($sOsmType) {
        $sSQL = 'select place_id from placex where';
        $sSQL .= ' osm_type = '.getDBQuoted($sOsmType);
        $sSQL .= ' and osm_id = '.$sOsmId;
        $sParentId = $oDB->getOne($sSQL);
        if (PEAR::isError($sParentId)) fail(pg_last_error($oDB->connection));
        if (!$sParentId) fail('Could not find place '.$sOsmType.' '.$sOsmId);
    }
    if ($sParentId) {
        $sPlacexSQL .= ' and place_id in (select place_id from place_addressline where address_place_id = '.$sParentId.' and isaddress)';
    }

    $sPlacexSQL .= " group by name->'name', address, postcode, country_code, placex.place_id";

    // Iterate over placeids
    // to get further hierarchical information
    //var_dump($sPlacexSQL);
    $aRes =& $oDB->query($sPlacexSQL);
    if (PEAR::isError($aRes)) fail(pg_last_error($oDB->connection));
    $fOutstream = fopen('php://output', 'w');
    while ($aRes->fetchInto($aRow)) {
    //var_dump($aRow);
        $iPlaceID = $aRow['place_id'];
        $sSQL = "select rank_address,get_name_by_language(name,$sLanguagePrefArraySQL) as localname from get_addressdata($iPlaceID, -1)";
        $sSQL .= ' WHERE isaddress';
        $sSQL .= ' order by rank_address desc,isaddress desc';
        $aAddressLines = $oDB->getAll($sSQL);
        if (PEAR::IsError($aAddressLines)) fail(pg_last_error($oDB->connection));


        $aOutput = array_fill(0, $iNumCol, '');
        // output address parts
        foreach ($aAddressLines as $aAddress) {
            if (isset($aColumnMapping[$aAddress['rank_address']])) {
                $aOutput[$aColumnMapping[$aAddress['rank_address']]] = $aAddress['localname'];
            }
        }
        // output postcode
        if (isset($aColumnMapping['postcode'])) {
            if ($aCMDResult['output-all-postcodes']) {
                $sSQL = 'select array_agg(px.postcode) from placex px join place_addressline pa ';
                $sSQL .= 'on px.place_id = pa.address_place_id ';
                $sSQL .= 'where pa.cached_rank_address in (5,11) ';
                $sSQL .= 'and pa.place_id in (select place_id from place_addressline where address_place_id in ('.substr($aRow['place_ids'], 1, -1).')) ';
                $sSQL .= 'group by postcode order by count(*) desc limit 1';
                $sRes = $oDB->getOne($sSQL);
                if (PEAR::IsError($sRes)) fail(pg_last_error($oDB->connection));
                $aOutput[$aColumnMapping['postcode']] = substr($sRes, 1, -1);
            } else {
                $aOutput[$aColumnMapping['postcode']] = $aRow['postcode'];
            }
        }
        if (isset($aColumnMapping['placeid'])) {
            $aOutput[$aColumnMapping['placeid']] = substr($aRow['place_ids'], 1, -1);
        }
        fputcsv($fOutstream, $aOutput);
    }
    fclose($fOutstream);
