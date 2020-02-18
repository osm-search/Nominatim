<?php

namespace Nominatim;

class Shell
{
    public function escapeFromArray($aCmd)
    {
        $aArgs = array_map(function ($sArg) {
            if (preg_match('/^-*\w+$/', $sArg)) return $sArg;
            return escapeshellarg($sArg);
        }, $aCmd);

        return join(' ', $aArgs);
    }
}
