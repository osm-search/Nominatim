<?php
/**
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This file is part of Nominatim. (https://nominatim.org)
 *
 * Copyright (C) 2022 by the Nominatim developer community.
 * For a full list of authors see the git log.
 */

namespace Nominatim\Token;

require_once(CONST_LibDir.'/SpecialSearchOperator.php');

/**
 * A word token describing a place type.
 */
class SpecialTerm
{
    /// Database word id, if applicable.
    private $iId;
    /// Class (or OSM tag key) of the place to look for.
    private $sClass;
    /// Type (or OSM tag value) of the place to look for.
    private $sType;
    /// Relationship of the operator to the object (see Operator class).
    private $iOperator;

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
     * Check if the token can be added to the given search.
     * Derive new searches by adding this token to an existing search.
     *
     * @param object  $oSearch      Partial search description derived so far.
     * @param object  $oPosition    Description of the token position within
                                    the query.
     *
     * @return True if the token is compatible with the search configuration
     *         given the position.
     */
    public function isExtendable($oSearch, $oPosition)
    {
        return !$oSearch->hasOperator()
               && $oPosition->isPhrase('')
               && ($this->iOperator != \Nominatim\Operator::NONE
                  || (!$oSearch->hasAddress() && !$oSearch->hasHousenumber() && !$oSearch->hasCountry()));
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
        $iSearchCost = 0;

        $iOp = $this->iOperator;
        if ($iOp == \Nominatim\Operator::NONE) {
            if ($oPosition->isFirstToken()
                || $oSearch->hasName()
                || $oSearch->getContext()->isBoundedSearch()
            ) {
                $iOp = \Nominatim\Operator::NAME;
                $iSearchCost += 3;
            } else {
                $iOp = \Nominatim\Operator::NEAR;
                $iSearchCost += 4;
                if (!$oPosition->isFirstToken()) {
                    $iSearchCost += 3;
                }
            }
        } elseif ($oPosition->isFirstToken()) {
            $iSearchCost += 2;
        } elseif ($oPosition->isLastToken()) {
            $iSearchCost += 4;
        } else {
            $iSearchCost += 6;
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
