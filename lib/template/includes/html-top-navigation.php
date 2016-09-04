<header class="container-fluid">
    <div class="row">
        <div class="col-xs-4">
            <div class="brand">
                <a href="<?php echo CONST_Website_BaseURL;?>">
                <img alt="logo" src="images/osm_logo.120px.png" width="30" height="30"/>
                <h1>Nominatim</h1>
                </a>
            </div>
        </div>
        <div id="last-updated" class="col-xs-4 text-center">
            <?php if (isset($sDataDate)){ ?>
                Data last updated:
                <br>
                <?php echo $sDataDate; ?>
            <?php } ?>
        </div>
        <div class="col-xs-4 text-right">
            <div class="btn-group">
                <button class="dropdown-toggle btn btn-sm btn-default" data-toggle="dropdown" role="button" aria-haspopup="true" aria-expanded="false">
                    About &amp; Help <span class="caret"></span>
                </button>
                <ul class="dropdown-menu dropdown-menu-right">
                    <li><a href="http://wiki.openstreetmap.org/wiki/Nominatim" target="_blank">Documentation</a></li>
                    <li><a href="http://wiki.openstreetmap.org/wiki/Nominatim/FAQ" target="_blank">FAQ</a></li>
                    <li role="separator" class="divider"></li>
                    <li><a href="#" class="" data-toggle="modal" data-target="#report-modal">Report problem with results</a></li>
                </ul>
            </div>
        </div>
    </div>
</header>

<div class="modal fade" id="report-modal">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                <h4 class="modal-title">Report a problem</h4>
            </div>
            <div class="modal-body">
                <?php include(CONST_BasePath.'/lib/template/includes/report-errors.php'); ?>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-default" data-dismiss="modal">OK</button>
            </div>
        </div>
    </div>
</div>
