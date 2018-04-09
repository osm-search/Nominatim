<?php

namespace Nominatim;

class Debug
{
    public static function newFunction($sHeading)
    {
        echo "<pre><h2>Debug output for $sHeading</h2></pre>\n";
    }

    public static function newSection($sHeading)
    {
        echo "<hr><pre><h3>$sHeading</h3></pre>\n";
    }

    public static function printVar($sHeading, $mVar)
    {
        echo '<pre><b>'.$sHeading. ':</b>  ';
        Debug::outputVar($mVar, str_repeat(' ', strlen($sHeading) + 3));
        echo "</pre>\n";
    }

    public static function fmtArrayVals($aArr)
    {
        return array('__debug_format' => 'array_vals', 'data' => $aArr);
    }

    public static function printDebugArray($sHeading, $oVar)
    {

        if ($oVar === null) {
            Debug::printVar($sHeading, 'null');
        } else {
            Debug::printVar($sHeading, $oVar->debugInfo());
        }
    }

    public static function printDebugTable($sHeading, $aVar)
    {
        echo '<b>'.$sHeading.":</b>\n";
        echo '<table border="1">';
        if (!empty($aVar)) {
            echo '<tr>';
            $aKeys = array();
            $aInfo = reset($aVar);
            if (!is_array($aInfo)) {
                $aInfo = $aInfo->debugInfo();
            }
            foreach ($aInfo as $sKey => $mVal) {
                echo '<th><small>'.$sKey.'</small></th>';
                $aKeys[] = $sKey;
            }
            echo '</tr>';
            foreach ($aVar as $oRow) {
                $aInfo = $oRow;
                if (!is_array($oRow)) {
                    $aInfo = $oRow->debugInfo();
                }
                echo '<tr>';
                foreach ($aKeys as $sKey) {
                    echo '<td><pre>';
                    if (isset($aInfo[$sKey])) {
                        Debug::outputVar($aInfo[$sKey], '');
                    }
                    echo '</pre></td>';
                }
                echo '<tr>';
            }
        }
        echo '</table>';
    }

    public static function printGroupTable($sHeading, $aVar)
    {
        echo '<b>'.$sHeading.":</b>\n";
        echo '<table border="1">';
        if (!empty($aVar)) {
            echo '<tr><th><small>Group</small></th>';
            $aKeys = array();
            $aInfo = reset(reset($aVar));
            if (!is_array($aInfo)) {
                $aInfo = $aInfo->debugInfo();
            }
            foreach ($aInfo as $sKey => $mVal) {
                echo '<th><small>'.$sKey.'</small></th>';
                $aKeys[] = $sKey;
            }
            echo '</tr>';
            foreach ($aVar as $sGrpKey => $aGroup) {
                foreach ($aGroup as $oRow) {
                    $aInfo = $oRow;
                    if (!is_array($oRow)) {
                        $aInfo = $oRow->debugInfo();
                    }
                    echo '<tr><td><pre>'.$sGrpKey.'</pre></td>';
                    foreach ($aKeys as $sKey) {
                        echo '<td><pre>';
                        if (!empty($aInfo[$sKey])) {
                            Debug::outputVar($aInfo[$sKey], '');
                        }
                        echo '</pre></td>';
                    }
                    echo '<tr>';
                }
            }
        }
        echo '</table>';
    }

    public static function printSQL($sSQL)
    {
        echo '<p><tt><font color="#aaa">'.$sSQL.'</font></tt></p>'."\n";
    }

    private static function outputVar($mVar, $sPreNL)
    {
        if (is_array($mVar) && !isset($mVar['__debug_format'])) {
            $sPre = '';
            foreach ($mVar as $mKey => $aValue) {
                echo $sPre;
                $iKeyLen = Debug::outputSimpleVar($mKey);
                echo ' => ';
                Debug::outputVar(
                    $aValue,
                    $sPreNL.str_repeat(' ', $iKeyLen + 4)
                );
                $sPre = "\n".$sPreNL;
            }
        } elseif (is_array($mVar) && isset($mVar['__debug_format'])) {
            if (!empty($mVar[data])) {
                $sPre = '';
                foreach ($mVar[data] as $mValue) {
                    echo $sPre;
                    Debug::outputSimpleVar($mValue);
                    $sPre = ', ';
                }
            }
        } else {
            Debug::outputSimpleVar($mVar);
        }
    }

    private static function outputSimpleVar($mVar)
    {
        if (is_bool($mVar)) {
            echo '<i>'.($mVar ? 'True' : 'False').'</i>';
            return $mVar ? 4 : 5;
        }

        if (is_string($mVar)) {
            echo "'$mVar'";
            return strlen($mVar) + 2;
        }

        echo (string)$mVar;
        return strlen((string)$mVar);
    }
}
