<?php

    $title = 'Internal Server Error';
    if ( $exception->getCode() == 400 ) {
        $title = 'Bad Request';
    }
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <style>
        em { font-weight: bold; font-family: monospace; color: #e00404; background-color: #ffeaea; }
    </style>
</head>
<body>
    <h1><?php echo $title ?></h1>
    
    <?php if (get_class($exception) == 'Nominatim\DatabaseError') { ?>

        <p>Nominatim has encountered an internal error while accessing the database.
           This may happen because the database is broken or because of a bug in
           the software.</p>

    <?php } else { ?>

        <p>Nominatim has encountered an error with your request.</p>

    <?php } ?>


    <h3>Details</h3>

    <?php echo $exception->getMessage() ?>

    <?php if (CONST_Debug) { ?>
        <p>
        Exception <em><?php echo get_class($exception) ?></em> thrown in <em><?php echo $exception->getFile() . '('. $exception->getLine() . ')' ?></em>.

        <?php if (get_class($exception) == 'Nominatim\DatabaseError') { ?>

            <h3>SQL Error</h3>
            <em><?php echo $exception->getSqlError() ?></em>

            <pre><?php echo $exception->getSqlDebugDump() ?></pre>

        <?php } ?>

        <h3>Stack trace</h3>
        <pre><?php echo $exception->getTraceAsString() ?></pre>

    <?php } ?>

    <p>
        If you feel this error is incorrect feel file an issue on
        <a href="https://github.com/openstreetmap/Nominatim/issues">Github</a>.

        Please include the error message above and the URL you used.
    </p>
</body>
</html>
