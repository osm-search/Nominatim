<?php
header('content-type: application/json; charset=UTF-8');
echo json_encode(
    [
     'status' => 'Bad Request',
     'message' => 'Nominatim has encountered an error with your request.',
     'details' => $sError
    ],
    JSON_PRETTY_PRINT
);
exit();
