@DB
Feature: Import of relations by osm2pgsql
    Testing specific relation problems related to members.

    Scenario: Don't import empty waterways
        When loading osm data
          """
          n1 Tamenity=prison,name=foo
          r1 Ttype=waterway,waterway=river,name=XZ Mn1@
          """
        Then place has no entry for R1
