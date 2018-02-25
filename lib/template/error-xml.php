<?php 
header('content-type: text/xml; charset=UTF-8'); 
$errorXml = <<<XML
<?xml version="1.0" encoding="UTF-8"?>
<error>
    <status>Bad Request</status>
    <message>Nominatim has encountered an error with your request.</message>
    <details>$sError</details>
</error>
XML;

$xml = new \SimpleXMLElement($errorXml);
echo $xml->asXML();

exit();
