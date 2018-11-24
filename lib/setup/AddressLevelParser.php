<?php

namespace Nominatim\Setup;

/**
 * Parses an address level description.
 */
class AddressLevelParser
{
    private $aLevels;

    public function __construct($sDescriptionFile)
    {
        $sJson = file_get_contents($sDescriptionFile);
        $this->aLevels = json_decode($sJson, true);
        if (!$this->aLevels) {
            switch (json_last_error()) {
                case JSON_ERROR_NONE:
                    break;
                case JSON_ERROR_DEPTH:
                    fail('JSON error - Maximum stack depth exceeded');
                    break;
                case JSON_ERROR_STATE_MISMATCH:
                    fail('JSON error - Underflow or the modes mismatch');
                    break;
                case JSON_ERROR_CTRL_CHAR:
                    fail('JSON error - Unexpected control character found');
                    break;
                case JSON_ERROR_SYNTAX:
                    fail('JSON error - Syntax error, malformed JSON');
                    break;
                case JSON_ERROR_UTF8:
                    fail('JSON error - Malformed UTF-8 characters, possibly incorrectly encoded');
                    break;
                default:
                    fail('JSON error - Unknown error');
                    break;
            }
        }
    }

    /**
     * Dump the description into a database table.
     *
     * @param object $oDB    Database conneciton to use.
     * @param string $sTable Name of table to create.
     *
     * @return null
     *
     * A new table is created. Any previously existing table is dropped.
     * The table has the following columns:
     * country, class, type, rank_search, rank_address.
     */
    public function createTable($oDB, $sTable)
    {
        chksql($oDB->query('DROP TABLE IF EXISTS '.$sTable));
        $sSql = 'CREATE TABLE '.$sTable;
        $sSql .= '(country_code varchar(2), class TEXT, type TEXT,';
        $sSql .= ' rank_search SMALLINT, rank_address SMALLINT)';
        chksql($oDB->query($sSql));

        $sSql = 'CREATE UNIQUE INDEX ON '.$sTable.'(country_code, class, type)';
        chksql($oDB->query($sSql));

        $sSql = 'INSERT INTO '.$sTable.' VALUES ';
        foreach ($this->aLevels as $aLevel) {
            $aCountries = array();
            if (isset($aLevel['countries'])) {
                foreach ($aLevel['countries'] as $sCountry) {
                    $aCountries[$sCountry] = getDBQuoted($sCountry);
                }
            } else {
                $aCountries['NULL'] = 'NULL';
            }
            foreach ($aLevel['tags'] as $sKey => $aValues) {
                foreach ($aValues as $sValue => $mRanks) {
                    $aFields = array(
                        getDBQuoted($sKey),
                        $sValue ? getDBQuoted($sValue) : 'NULL'
                    );
                    if (is_array($mRanks)) {
                        $aFields[] = (string) $mRanks[0];
                        $aFields[] = (string) $mRanks[1];
                    } else {
                        $aFields[] = (string) $mRanks;
                        $aFields[] = (string) $mRanks;
                    }
                    $sLine = ','.join(',', $aFields).'),';

                    foreach ($aCountries as $sCountries) {
                        $sSql .= '('.$sCountries.$sLine;
                    }
                }
            }
        }
        chksql($oDB->query(rtrim($sSql, ',')));
    }
}
