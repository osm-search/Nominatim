<?php

namespace Nominatim\Token;

require_once(CONST_BasePath.'/lib/SpecialSearchOperator.php');

/**
 * A word token describing a place type.
 */
class SpecialTerm
{
    public $iId;
    public $sClass;
    public $sType;
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
                           'operator' => Operator::toString($this->iOperator)
                          )
               );
    }
}
