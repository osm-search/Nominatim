-- Splits the line at the given point and returns the two parts
-- in a multilinestring.
CREATE OR REPLACE FUNCTION split_line_on_node(line GEOMETRY, point GEOMETRY)
RETURNS GEOMETRY
  AS $$
BEGIN
  RETURN ST_Split(line, ST_ClosestPoint(line, point));
END;
$$
LANGUAGE plpgsql;
