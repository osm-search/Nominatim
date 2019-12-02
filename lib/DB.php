<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/DatabaseError.php');

/**
 * Uses PDO to access the database specified in the CONST_Database_DSN
 * setting.
 */
class DB
{
    protected $connection;

    public function __construct($sDSN = CONST_Database_DSN)
    {
        $this->sDSN = $sDSN;
    }

    public function connect($bNew = false, $bPersistent = true)
    {
        if (isset($this->connection) && !$bNew) {
            return true;
        }
        $aConnOptions = array(
                         \PDO::ATTR_ERRMODE            => \PDO::ERRMODE_EXCEPTION,
                         \PDO::ATTR_DEFAULT_FETCH_MODE => \PDO::FETCH_ASSOC,
                         \PDO::ATTR_PERSISTENT         => $bPersistent
        );

        // https://secure.php.net/manual/en/ref.pdo-pgsql.connection.php
        try {
            $conn = new \PDO($this->sDSN, null, null, $aConnOptions);
        } catch (\PDOException $e) {
            $sMsg = 'Failed to establish database connection:' . $e->getMessage();
            throw new \Nominatim\DatabaseError($sMsg, 500, null, $e->getMessage());
        }

        $conn->exec("SET DateStyle TO 'sql,european'");
        $conn->exec("SET client_encoding TO 'utf-8'");
        $iMaxExecution = ini_get('max_execution_time');
        if ($iMaxExecution > 0) $conn->setAttribute(\PDO::ATTR_TIMEOUT, $iMaxExecution); // seconds

        $this->connection = $conn;
        return true;
    }

    // returns the number of rows that were modified or deleted by the SQL
    // statement. If no rows were affected returns 0.
    public function exec($sSQL, $aInputVars = null, $sErrMessage = 'Database query failed')
    {
        $val = null;
        try {
            if (isset($aInputVars)) {
                $stmt = $this->connection->prepare($sSQL);
                $stmt->execute($aInputVars);
            } else {
                $val = $this->connection->exec($sSQL);
            }
        } catch (\PDOException $e) {
            throw new \Nominatim\DatabaseError($sErrMessage, 500, null, $e, $sSQL);
        }
        return $val;
    }

    /**
     * Executes query. Returns first row as array.
     * Returns false if no result found.
     *
     * @param string  $sSQL
     *
     * @return array[]
     */
    public function getRow($sSQL, $aInputVars = null, $sErrMessage = 'Database query failed')
    {
        try {
            $stmt = $this->getQueryStatement($sSQL, $aInputVars, $sErrMessage);
            $row = $stmt->fetch();
        } catch (\PDOException $e) {
            throw new \Nominatim\DatabaseError($sErrMessage, 500, null, $e, $sSQL);
        }
        return $row;
    }

    /**
     * Executes query. Returns first value of first result.
     * Returns false if no results found.
     *
     * @param string  $sSQL
     *
     * @return array[]
     */
    public function getOne($sSQL, $aInputVars = null, $sErrMessage = 'Database query failed')
    {
        try {
            $stmt = $this->getQueryStatement($sSQL, $aInputVars, $sErrMessage);
            $row = $stmt->fetch(\PDO::FETCH_NUM);
            if ($row === false) return false;
        } catch (\PDOException $e) {
            throw new \Nominatim\DatabaseError($sErrMessage, 500, null, $e, $sSQL);
        }
        return $row[0];
    }

    /**
     * Executes query. Returns array of results (arrays).
     * Returns empty array if no results found.
     *
     * @param string  $sSQL
     *
     * @return array[]
     */
    public function getAll($sSQL, $aInputVars = null, $sErrMessage = 'Database query failed')
    {
        try {
            $stmt = $this->getQueryStatement($sSQL, $aInputVars, $sErrMessage);
            $rows = $stmt->fetchAll();
        } catch (\PDOException $e) {
            throw new \Nominatim\DatabaseError($sErrMessage, 500, null, $e, $sSQL);
        }
        return $rows;
    }

    /**
     * Executes query. Returns array of the first value of each result.
     * Returns empty array if no results found.
     *
     * @param string  $sSQL
     *
     * @return array[]
     */
    public function getCol($sSQL, $aInputVars = null, $sErrMessage = 'Database query failed')
    {
        $aVals = array();
        try {
            $stmt = $this->getQueryStatement($sSQL, $aInputVars, $sErrMessage);

            while (($val = $stmt->fetchColumn(0)) !== false) { // returns first column or false
                $aVals[] = $val;
            }
        } catch (\PDOException $e) {
            throw new \Nominatim\DatabaseError($sErrMessage, 500, null, $e, $sSQL);
        }
        return $aVals;
    }

    /**
     * Executes query. Returns associate array mapping first value to second value of each result.
     * Returns empty array if no results found.
     *
     * @param string  $sSQL
     *
     * @return array[]
     */
    public function getAssoc($sSQL, $aInputVars = null, $sErrMessage = 'Database query failed')
    {
        try {
            $stmt = $this->getQueryStatement($sSQL, $aInputVars, $sErrMessage);

            $aList = array();
            while ($aRow = $stmt->fetch(\PDO::FETCH_NUM)) {
                $aList[$aRow[0]] = $aRow[1];
            }
        } catch (\PDOException $e) {
            throw new \Nominatim\DatabaseError($sErrMessage, 500, null, $e, $sSQL);
        }
        return $aList;
    }

    /**
     * Executes query. Returns a PDO statement to iterate over.
     *
     * @param string  $sSQL
     *
     * @return PDOStatement
     */
    public function getQueryStatement($sSQL, $aInputVars = null, $sErrMessage = 'Database query failed')
    {
        try {
            if (isset($aInputVars)) {
                $stmt = $this->connection->prepare($sSQL);
                $stmt->execute($aInputVars);
            } else {
                $stmt = $this->connection->query($sSQL);
            }
        } catch (\PDOException $e) {
            throw new \Nominatim\DatabaseError($sErrMessage, 500, null, $e, $sSQL);
        }
        return $stmt;
    }

    /**
     * St. John's Way => 'St. John\'s Way'
     *
     * @param string  $sVal  Text to be quoted.
     *
     * @return string
     */
    public function getDBQuoted($sVal)
    {
        return $this->connection->quote($sVal);
    }

    /**
     * Like getDBQuoted, but takes an array.
     *
     * @param array  $aVals  List of text to be quoted.
     *
     * @return array[]
     */
    public function getDBQuotedList($aVals)
    {
        return array_map(function ($sVal) {
            return $this->getDBQuoted($sVal);
        }, $aVals);
    }

    /**
     * [1,2,'b'] => 'ARRAY[1,2,'b']''
     *
     * @param array  $aVals  List of text to be quoted.
     *
     * @return string
     */
    public function getArraySQL($a)
    {
        return 'ARRAY['.join(',', $a).']';
    }

    /**
     * Check if a table exists in the database. Returns true if it does.
     *
     * @param string  $sTableName
     *
     * @return boolean
     */
    public function tableExists($sTableName)
    {
        $sSQL = 'SELECT count(*) FROM pg_tables WHERE tablename = :tablename';
        return ($this->getOne($sSQL, array(':tablename' => $sTableName)) == 1);
    }

    /**
    * Check if an index exists in the database. Optional filtered by tablename
    *
    * @param string  $sTableName
    *
    * @return boolean
    */
    public function indexExists($sIndexName, $sTableName = null)
    {
        return in_array($sIndexName, $this->getListOfIndices($sTableName));
    }

    /**
    * Returns a list of index names in the database, optional filtered by tablename
    *
    * @param string  $sTableName
    *
    * @return array
    */
    public function getListOfIndices($sTableName = null)
    {
        //  table_name            | index_name                      | column_name
        // -----------------------+---------------------------------+--------------
        //  country_name          | idx_country_name_country_code   | country_code
        //  country_osm_grid      | idx_country_osm_grid_geometry   | geometry
        //  import_polygon_delete | idx_import_polygon_delete_osmid | osm_id
        //  import_polygon_delete | idx_import_polygon_delete_osmid | osm_type
        //  import_polygon_error  | idx_import_polygon_error_osmid  | osm_id
        //  import_polygon_error  | idx_import_polygon_error_osmid  | osm_type
        $sSql = <<< END
SELECT
    t.relname as table_name,
    i.relname as index_name,
    a.attname as column_name
FROM
    pg_class t,
    pg_class i,
    pg_index ix,
    pg_attribute a
WHERE
    t.oid = ix.indrelid
    and i.oid = ix.indexrelid
    and a.attrelid = t.oid
    and a.attnum = ANY(ix.indkey)
    and t.relkind = 'r'
    and i.relname NOT LIKE 'pg_%'
    FILTERS
 ORDER BY
    t.relname,
    i.relname,
    a.attname
END;

        $aRows = null;
        if ($sTableName) {
            $sSql = str_replace('FILTERS', 'and t.relname = :tablename', $sSql);
            $aRows = $this->getAll($sSql, array(':tablename' => $sTableName));
        } else {
            $sSql = str_replace('FILTERS', '', $sSql);
            $aRows = $this->getAll($sSql);
        }

        $aIndexNames = array_unique(array_map(function ($aRow) {
            return $aRow['index_name'];
        }, $aRows));
        sort($aIndexNames);

        return $aIndexNames;
    }

    /**
     * Since the DSN includes the database name, checks if the connection works.
     *
     * @return boolean
     */
    public function databaseExists()
    {
        $bExists = true;
        try {
            $this->connect(true);
        } catch (\Nominatim\DatabaseError $e) {
            $bExists = false;
        }
        return $bExists;
    }

    /**
     * e.g. 9.6, 10, 11.2
     *
     * @return float
     */
    public function getPostgresVersion()
    {
        $sVersionString = $this->getOne('SHOW server_version_num');
        preg_match('#([0-9]?[0-9])([0-9][0-9])[0-9][0-9]#', $sVersionString, $aMatches);
        return (float) ($aMatches[1].'.'.$aMatches[2]);
    }

    /**
     * e.g. 2, 2.2
     *
     * @return float
     */
    public function getPostgisVersion()
    {
        $sVersionString = $this->getOne('select postgis_lib_version()');
        preg_match('#^([0-9]+)[.]([0-9]+)[.]#', $sVersionString, $aMatches);
        return (float) ($aMatches[1].'.'.$aMatches[2]);
    }

    public static function parseDSN($sDSN)
    {
        // https://secure.php.net/manual/en/ref.pdo-pgsql.connection.php
        $aInfo = array();
        if (preg_match('/^pgsql:(.+)$/', $sDSN, $aMatches)) {
            foreach (explode(';', $aMatches[1]) as $sKeyVal) {
                list($sKey, $sVal) = explode('=', $sKeyVal, 2);
                if ($sKey == 'host') $sKey = 'hostspec';
                if ($sKey == 'dbname') $sKey = 'database';
                if ($sKey == 'user') $sKey = 'username';
                $aInfo[$sKey] = $sVal;
            }
        }
        return $aInfo;
    }
}
