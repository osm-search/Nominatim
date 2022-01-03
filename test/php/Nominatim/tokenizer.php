<?php
/**
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * This file is part of Nominatim. (https://nominatim.org)
 *
 * Copyright (C) 2022 by the Nominatim developer community.
 * For a full list of authors see the git log.
 */

namespace Nominatim;

class Tokenizer
{
    private $oDB;

    public function __construct(&$oDB)
    {
        $this->oDB =& $oDB;
    }

    public function checkStatus()
    {
    }
}
