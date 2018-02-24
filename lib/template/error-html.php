<?php

header('HTTP/1.0 400 Bad Request');
header('Content-type: text/html; charset=utf-8');
    echo '<html><body><h1>Bad Request</h1>';
    echo '<p>Nominatim has encountered an error with your request.</p>';
    echo '<p><b>Details:</b> '.$sError.'</p>';
    echo '<p>If you feel this error is incorrect feel file an issue on <a href="https://github.com/openstreetmap/Nominatim/issues">Github</a>. ';
    echo 'Please include the error message above and the URL you used.</p>';
    echo "\n</body></html>\n";
    exit;
