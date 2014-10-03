-- Splits the line at the given point and returns the two parts
-- in a multilinestring.
CREATE OR REPLACE FUNCTION split_line_on_node(line GEOMETRY, point GEOMETRY)
RETURNS GEOMETRY
  AS $$
DECLARE
  frac FLOAT;
BEGIN
  frac := ST_Line_Locate_Point(line, point);
  RETURN ST_Collect(ST_Line_Substring(line, 0, frac),
         ST_Line_Substring(line, frac, 1));
END
$$
LANGUAGE plpgsql;
