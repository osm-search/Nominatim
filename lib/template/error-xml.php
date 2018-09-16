<error>
    <code><?php echo $exception->getCode() ?></code>
    <message><?php echo $exception->getMessage() ?></message>
    <?php if (CONST_Debug) { ?>
    <details><?php echo $exception->getFile() . '('. $exception->getLine() . ')' ?></details>
    <?php } ?>
</error>