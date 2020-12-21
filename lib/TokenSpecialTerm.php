<?php

namespace Nominatim\Token;

require_once(CONST_LibDir.'/SpecialSearchOperator.php');

/**
 * A word token describing a place type.
 */
class SpecialTerm
{
    /// Database word id, if applicable.
    public $iId;
    /// Class (or OSM tag key) of the place to look for.
    public $sClass;
    /// Type (or OSM tag value) of the place to look for.
    public $sType;
    /// Relationship of the operator to the object (see Operator class).
    public $iOperator;

    public function __construct($iID, $sClass, $sType, $iOperator)
    {
        $this->iId = $iID;
        $this->sClass = $sClass;
        $this->sType = $sType;
        $this->iOperator = $iOperator;
    }

    public function debugInfo()
    {
        return array(
                'ID' => $this->iId,
                'Type' => 'special term',
                'Info' => array(
                           'class' => $this->sClass,
                           'type' => $this->sType,
                           'operator' => \Nominatim\Operator::toString($this->iOperator)
                          )
               );
    }
}
