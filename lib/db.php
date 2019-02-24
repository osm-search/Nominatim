<?php

namespace Nominatim;

require_once(CONST_BasePath.'/lib/DatabaseError.php');

class DB
{
    public $connection;

    public function __construct($sDSN = CONST_Database_DSN)
    {
        $this->sDSN = $sDSN;
    }

    public function connect($bNew = false, $bPersistent = true)
    {
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
    public function exec($sSQL)
    {
        $val = null;
        try {
            $val = $this->connection->exec($sSQL);
        } catch (\PDOException $e) {
            throw new \Nominatim\DatabaseError('Database query failed', 500, null, $e, $sSQL);
        }
        return $val;
    }

    public function getRow($sSQL)
    {
        try {
            $stmt = $this->connection->query($sSQL);
            $row = $stmt->fetch();
        } catch (\PDOException $e) {
            throw new \Nominatim\DatabaseError('Database query failed', 500, null, $e, $sSQL);
        }
        return $row;
    }

    public function getOne($sSQL)
    {
        try {
            $stmt = $this->connection->query($sSQL);
            $row = $stmt->fetch(\PDO::FETCH_NUM);
            if ($row === false) return false;
        } catch (\PDOException $e) {
            throw new \Nominatim\DatabaseError('Database query failed', 500, null, $e, $sSQL);
        }
        return $row[0];
    }

    public function getAll($sSQL)
    {
        try {
            $stmt = $this->connection->query($sSQL);
            $rows = $stmt->fetchAll();
        } catch (\PDOException $e) {
            throw new \Nominatim\DatabaseError('Database query failed', 500, null, $e, $sSQL);
        }
        return $rows;
    }

    public function getCol($sSQL)
    {
        $aVals = array();
        try {
            $stmt = $this->connection->query($sSQL);
            while ($val = $stmt->fetchColumn(0)) { // returns first column or false
                $aVals[] = $val;
            }
        } catch (\PDOException $e) {
            throw new \Nominatim\DatabaseError('Database query failed', 500, null, $e, $sSQL);
        }
        return $aVals;
    }

    public function getAssoc($sSQL)
    {
        try {
            $stmt = $this->connection->query($sSQL);
            $aList = array();
            while ($aRow = $stmt->fetch(\PDO::FETCH_NUM)) {
                $aList[$aRow[0]] = $aRow[1];
            }
        } catch (\PDOException $e) {
            throw new \Nominatim\DatabaseError('Database query failed', 500, null, $e, $sSQL);
        }
        return $aList;
    }


    // St. John's Way => 'St. John\'s Way'
    public function getDBQuoted($sVal)
    {
        return $this->connection->quote($sVal);
    }

    public function getDBQuotedList($aVals)
    {
        return array_map(function ($sVal) {
            return $this->getDBQuoted($sVal);
        }, $aVals);
    }

    public function getArraySQL($a)
    {
        return 'ARRAY['.join(',', $a).']';
    }

    public function getLastError()
    {
        // https://secure.php.net/manual/en/pdo.errorinfo.php
        return $this->connection->errorInfo();
    }

    public function tableExists($sTableName)
    {
        $sSQL = 'SELECT count(*) FROM pg_tables WHERE tablename = '.$this->getDBQuoted($sTableName);
        return ($this->getOne($sSQL) == 1);
    }

    public function getPostgresVersion()
    {
        $sVersionString = $this->getOne('SHOW server_version_num');
        preg_match('#([0-9]?[0-9])([0-9][0-9])[0-9][0-9]#', $sVersionString, $aMatches);
        return (float) ($aMatches[1].'.'.$aMatches[2]);
    }

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
        if (preg_match('/^pgsql:(.+)/', $sDSN, $aMatches)) {
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
