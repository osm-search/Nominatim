<?php

$phpPhraseSettingsFile = $argv[1];
<<<<<<< HEAD
$jsonPhraseSettingsFile = dirname($phpPhraseSettingsFile).'/'.basename($phpPhraseSettingsFile, '.php').'.json';

if (file_exists($phpPhraseSettingsFile) && !file_exists($jsonPhraseSettingsFile)) {
=======
$jsonPhraseSettingsFile = dirname($phpPhraseSettingsFile)."/".basename($phpPhraseSettingsFile, ".php").".json";

if(file_exists($phpPhraseSettingsFile) && !file_exists($jsonPhraseSettingsFile))
{
>>>>>>> 3d939458... Changed phrase_settings.py to phrase-settings.json and added migration function for old php settings file.
    include $phpPhraseSettingsFile;

    $data = array();

    if (isset($aTagsBlacklist))
        $data['blackList'] = $aTagsBlacklist;
    if (isset($aTagsWhitelist))
        $data['whiteList'] = $aTagsWhitelist;

    $jsonFile = fopen($jsonPhraseSettingsFile, 'w');
    fwrite($jsonFile, json_encode($data));
    fclose($jsonFile);
<<<<<<< HEAD
}
=======
}
>>>>>>> 3d939458... Changed phrase_settings.py to phrase-settings.json and added migration function for old php settings file.
