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

    public function getId()
    {
        return $this->iId;
    }

    /**
     * Derive new searches by adding this token to an existing search.
     *
     * @param object  $oSearch      Partial search description derived so far.
     * @param object  $oPosition    Description of the token position within
                                    the query.
     *
     * @return SearchDescription[] List of derived search descriptions.
     */
    public function extendSearch($oSearch, $oPosition)
    {
        if ($oSearch->hasOperator() || !$oPosition->isPhrase('')) {
            return array();
        }

        $iSearchCost = 2;

        $iOp = $this->iOperator;
        if ($iOp == \Nominatim\Operator::NONE) {
            if ($oSearch->hasName() || $oSearch->getContext()->isBoundedSearch()) {
                $iOp = \Nominatim\Operator::NAME;
            } else {
                $iOp = \Nominatim\Operator::NEAR;
            }
            $iSearchCost += 2;
        } elseif (!$oPosition->isFirstToken() && !$oPosition->isLastToken()) {
            $iSearchCost += 2;
        }
        if ($oSearch->hasHousenumber()) {
            $iSearchCost ++;
        }

        $oNewSearch = $oSearch->clone($iSearchCost);
        $oNewSearch->setPoiSearch($iOp, $this->sClass, $this->sType);

        return array($oNewSearch);
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

    public function debugCode()
    {
        return 'S';
    }
}
