<?php

namespace Nominatim;

/**
 * Operators describing special searches.
 */
abstract class Operator
{
    /// No operator selected.
    const NONE = 0;
    /// Search for POI of the given type.
    const TYPE = 1;
    /// Search for POIs near the given place.
    const NEAR = 2;
    /// Search for POIS in the given place.
    const IN = 3;
    /// Search for POIS named as given.
    const NAME = 4;
    /// Search for postcodes.
    const POSTCODE = 5;

    private static $aConstantNames = null;


    public static function toString($iOperator)
    {
        if ($iOperator == Operator::NONE) {
            return '';
        }

        if (Operator::$aConstantNames === null) {
            $oReflector = new \ReflectionClass('Nominatim\Operator');
            $aConstants = $oReflector->getConstants();

            Operator::$aConstantNames = array();
            foreach ($aConstants as $sName => $iValue) {
                Operator::$aConstantNames[$iValue] = $sName;
            }
        }

        return Operator::$aConstantNames[$iOperator];
    }
}
