#!/usr/bin/php -Cq
<?php

$hFile = @fopen("wikidatawiki-20130623-pages-articles.xml", "r");

$hFileEntity = fopen("entity.csv", "w");
$hFileEntityLabel = fopen("entity_label.csv", "w");
$hFileEntityDescription = fopen("entity_description.csv", "w");
$hFileEntityAlias = fopen("entity_alias.csv", "w");
$hFileEntityLink = fopen("entity_link.csv", "w");
$hFileEntityProperty = fopen("entity_property.csv", "w");

$iCount = 0;

$sTitle = '';
$iNS = false;
$iID = false;

if ($hFile) {
    while (($sLine = fgets($hFile, 4000000)) !== false) {
        if (substr($sLine, 0, 11) == '    <title>') {
            $sTitle = substr($sLine, 11, -9);
        } elseif (substr($sLine, 0, 8) == '    <ns>') {
            $iNS = (int)substr($sLine, 8, -6);
        } elseif (substr($sLine, 0, 8) == '    <id>') {
            $iID = (int)substr($sLine, 8, -6);
        } elseif (substr($sLine, 0, 33) == '      <text xml:space="preserve">') {
            if ($iNS == -2) continue;
            if ($iNS == -1) continue;
            if ($iNS == 1) continue;
            if ($iNS == 2) continue;
            if ($iNS == 3) continue;
            if ($iNS == 4) continue;
            if ($iNS == 5) continue;
            if ($iNS == 6) continue;
            if ($iNS == 7) continue;
            if ($iNS == 8) continue;
            if ($iNS == 9) continue;
            if ($iNS == 10) continue;
            if ($iNS == 11) continue;
            if ($iNS == 12) continue;
            if ($iNS == 13) continue;
            if ($iNS == 14) continue;
            if ($iNS == 15) continue;
            if ($iNS == 121) continue;
            if ($iNS == 123) continue;
            if ($iNS == 829) continue;
            if ($iNS == 1198) continue;
            if ($iNS == 1199) continue;
            $sText = html_entity_decode(substr($sLine, 33, -8), ENT_COMPAT, 'UTF-8');
            $aArticle = json_decode($sText, true);

            if (array_diff(array_keys($aArticle), array("label", "description", "aliases", "links", "entity", "claims", "datatype")) != array()) {
                // DEBUG
                var_dump($sTitle);
                var_dump(array_keys($aArticle));
                var_dump($aArticle);
                exit;
            }

            $iPID = $iQID = null;
            if ($aArticle['entity'][0] == 'p') {
                $iPID = (int) substr($aArticle['entity'], 1);
            } elseif ($aArticle['entity'][0] == 'q') {
                $iQID = (int) substr($aArticle['entity'], 1);
            } else {
                continue;
            }

            echo ".";

            fputcsv($hFileEntity, array($iID, $sTitle, $iPID, $iQID, @$aArticle['datatype']));

            foreach ($aArticle['label'] as $sLang => $sLabel) {
                fputcsv($hFileEntityLabel, array($iID, $sLang, $sLabel));
                // echo "insert into entity_label values (".$iID.",'".pg_escape_string($sLang)."','".pg_escape_string($sLabel)."');\n";
            }

            foreach ($aArticle['description'] as $sLang => $sLabel) {
                fputcsv($hFileEntityDescription, array($iID, $sLang, $sLabel));
                // echo "insert into entity_description values (".$iID.",'".pg_escape_string($sLang)."','".pg_escape_string($sLabel)."');\n";
            }

            foreach ($aArticle['aliases'] as $sLang => $aLabels) {
                $aUniqueAlias = array();
                foreach ($aLabels as $sLabel) {
                    if (!isset($aUniqueAlias[$sLabel]) && $sLabel) {
                        fputcsv($hFileEntityAlias, array($iID, $sLang, $sLabel));
                        // echo "insert into entity_alias values (".$iID.",'".pg_escape_string($sLang)."','".pg_escape_string($sLabel)."');\n";
                        $aUniqueAlias[$sLabel] = true;
                    }
                }
            }

            foreach ($aArticle['links'] as $sLang => $sLabel) {
                fputcsv($hFileEntityLink, array($iID, $sLang, $sLabel));
                // echo "insert into entity_link values (".$iID.",'".pg_escape_string($sLang)."','".pg_escape_string($sLabel)."');\n";
            }


            if (isset($aArticle['claims'])) {
                //
                foreach ($aArticle['claims'] as $iClaim => $aClaim) {
                    //
                    $bFail = false;
                    if ($aClaim['m'][0] == 'novalue') continue;
                    if ($aClaim['m'][0] == 'somevalue') continue;
                    $iPID = (int)$aClaim['m'][1];
                    if ($aClaim['m'][0] != 'value') $bFail = true;
                    if ($aClaim['m'][2]== 'wikibase-entityid') {
                        //
                        if ($aClaim['m'][3]['entity-type'] != 'item') $bFail = true;
                        fputcsv($hFileEntityProperty, array($iID, $iClaim, $iPID, null, $aClaim['m'][3]['numeric-id'], null, null));
                        // echo "insert into entity_property values (nextval('seq_entity_property'),".$iID.",".$iPID.",null,".$aClaim['m'][3]['numeric-id'].",null);\n";
                    } elseif ($aClaim['m'][2] == 'globecoordinate') {
                        //
                        if ($aClaim['m'][3]['globe'] != 'http://www.wikidata.org/entity/Q2') $bFail = true;
                        fputcsv($hFileEntityProperty, array($iID, $iClaim, $iPID, null, null, "SRID=4326;POINT(".((float) $aClaim['m'][3]['longitude'])." ".((float)$aClaim['m'][3]['latitude']).")", null));
                        // echo "insert into entity_property values (nextval('seq_entity_property'),".$iID.",".$iPID.",null,null,ST_SetSRID(ST_MakePoint(".((float)$aClaim['m'][3]['longitude']).", ".((float)$aClaim['m'][3]['latitude'])."),4326));\n";
                    } elseif ($aClaim['m'][2] == 'time') {
                        // TODO!
                        /*
                        if ($aClaim['m'][3]['calendarmodel'] == 'http://www.wikidata.org/entity/Q1985727') {
                            // Gregorian
                            if (preg_match('#(\\+|-)0*([0-9]{4})-([0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2})Z#', $aClaim['m'][3]['time'], $aMatch)) {
                                if ((int)$aMatch[2] < 4700 && ) {
                                    $sDateString = $aMatch[2].'-'.$aMatch[3].($aClaim['m'][3]['timezone']>=0?'+':'').$aClaim['m'][3]['timezone'].($aMatch[1]=='-'?' bc':'');
                                    fputcsv($hFileEntityProperty, array($iID,$iClaim,$iPID,null,null,null,$sDateString));
                                }
                            } else {
                                // $bFail = true;
                            }
                        } elseif ( $aClaim['m'][3]['calendarmodel'] != 'http://www.wikidata.org/entity/Q1985786') {
                            // Julian
                            if (preg_match('#(\\+|-)0*([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}:[0-9]{2}:[0-9]{2})Z#', $aClaim['m'][3]['time'], $aMatch)) {
                                var_dump($aMatch);
                                exit;
                                $iDayCount = juliantojd(2, 11, 1732);
                                var_dump($iDayCount, jdtogregorian($iDayCount));
                        } else {
                            $bFail = true;
                            exit;
                        }
                        exit;
                    } else {
                        // $bFail = true;
                    }
                    */
                    } elseif ($aClaim['m'][2] == 'string') {
                        // echo "insert into entity_property values (nextval('seq_entity_property'),".$iID.",".$iPID.",'".pg_escape_string($aClaim['m'][3])."',null,null);\n";
                        fputcsv($hFileEntityProperty, array($iID, $iClaim, $iPID, $aClaim['m'][3], null, null, null));
                    } else {
                        $bFail = true;
                    }

                    // Don't care about sources:    if ($aClaim['refs'] != array()) $bFail = true;

                    if ($bFail) {
                        var_dump($sTitle);
                        var_dump($aClaim);
                    } else {
                        // process
                    }
                }
            }
        }
    }
    fclose($hFile);
    fclose($hFileEntity);
    fclose($hFileEntityLabel);
    fclose($hFileEntityDescription);
    fclose($hFileEntityAlias);
    fclose($hFileEntityLink);
    fclose($hFileEntityProperty);
}
