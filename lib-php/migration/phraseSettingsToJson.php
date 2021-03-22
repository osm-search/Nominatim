<?php

$phpPhraseSettingsFile = $argv[1];
$jsonPhraseSettingsFile = dirname($phpPhraseSettingsFile).'/'.basename($phpPhraseSettingsFile, '.php').'.json';

if (file_exists($phpPhraseSettingsFile) && !file_exists($jsonPhraseSettingsFile)) {
    include $phpPhraseSettingsFile;

    $data = array();

    if (isset($aTagsBlacklist))
        $data['blackList'] = $aTagsBlacklist;
    if (isset($aTagsWhitelist))
        $data['whiteList'] = $aTagsWhitelist;

    $jsonFile = fopen($jsonPhraseSettingsFile, 'w');
    fwrite($jsonFile, json_encode($data));
    fclose($jsonFile);
}
