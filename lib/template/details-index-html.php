<?php
    header("content-type: text/html; charset=UTF-8");
?>
<?php include(CONST_BasePath.'/lib/template/includes/html-header.php'); ?>
    <link href="css/common.css" rel="stylesheet" type="text/css" />
    <link href="css/details.css" rel="stylesheet" type="text/css" />
</head>


<body id="details-index-page">
    <div class="container">
        <div class="row">
            <div class="col-md-12">

                <h1>Show details for place</h1>

                <div class="search-form">
                    <h4>Search by place id</h4>

                    <form class="form-inline" action="details.php">
                        <input type="edit" class="form-control input-sm" pattern="^[0-9]+$" name="place_id" placeholder="12345" />
                        <input type="submit" class="btn btn-primary btn-sm" value="Show" />
                    </form>
                </div>

                <div class="search-form">
                    <h4>Search by OSM type and OSM id</h4>

                    <form id="form-by-type-and-id" class="form-inline" action="details.php">
                        <input type="edit" class="form-control input-sm" pattern="^[NWR][0-9]+$" placeholder="N123 or W123 or R123" />
                        <input type="hidden" name="osmtype" />
                        <input type="hidden" name="osmid" />
                        <input type="submit" class="btn btn-primary btn-sm" value="Show" />
                    </form>
                </div>

                <div class="search-form">
                    <h4>Search by openstreetmap.org URL</h4>

                    <form id="form-by-osm-url" class="form-inline" action="details.php">
                        <input type="edit" class="form-control input-sm" pattern=".*openstreetmap.*" placeholder="https://www.openstreetmap.org/relation/123" />
                        <input type="hidden" name="osmtype" />
                        <input type="hidden" name="osmid" />
                        <input type="submit" class="btn btn-primary btn-sm" value="Show" />
                    </form>
                </div>

            </div>
        </div>
    </div>


    <?php include(CONST_BasePath.'/lib/template/includes/html-footer.php'); ?>
</body>
</html>
