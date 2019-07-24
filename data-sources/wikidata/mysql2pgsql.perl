#!/usr/bin/perl -w
# mysql2pgsql
# MySQL to PostgreSQL dump file converter
#
# For usage: perl mysql2pgsql.perl --help
#
# ddl statments are changed but none or only minimal real data
# formatting are done.
# data consistency is up to the DBA.
#
# (c) 2004-2007 Jose M Duarte and Joseph Speigle ... gborg
#
# (c) 2000-2004 Maxim Rudensky  <fonin@omnistaronline.com>
# (c) 2000 Valentine Danilchuk  <valdan@ziet.zhitomir.ua>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. All advertising materials mentioning features or use of this software
#    must display the following acknowledgement:
# This product includes software developed by the Max Rudensky
# and its contributors.
# 4. Neither the name of the author nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

use Getopt::Long;

use POSIX;

use strict;
use warnings;


# main sections
# -------------
# 1 variable declarations
# 2 subroutines
# 3 get commandline options and specify help statement
# 4 loop through file and process
# 5. print_plpgsql function prototype

#################################################################
#  1.  variable declarations
#################################################################
# command line options
my( $ENC_IN, $ENC_OUT, $PRESERVE_CASE, $HELP, $DEBUG, $SCHEMA, $LOWERCASE, $CHAR2VARCHAR, $NODROP, $SEP_FILE, $opt_debug, $opt_help, $opt_schema, $opt_preserve_case, $opt_char2varchar, $opt_nodrop, $opt_sepfile, $opt_enc_in, $opt_enc_out );
# variables for constructing pre-create-table entities
my $pre_create_sql='';    # comments, 'enum' constraints preceding create table statement
my $auto_increment_seq= '';    # so we can easily substitute it if we need a default value
my $create_sql='';    # all the datatypes in the create table section
my $post_create_sql='';   # create indexes, foreign keys, table comments
my $function_create_sql = '';  # for the set (function,trigger) and CURRENT_TIMESTAMP ( function,trigger )
#  constraints
my ($type, $column_valuesStr, @column_values, $value );
my %constraints=(); #  holds values constraints used to emulate mysql datatypes (e.g. year, set)
# datatype conversion variables
my ( $index,$seq);
my ( $column_name, $col, $quoted_column);
my ( @year_holder, $year, $constraint_table_name);
my $table="";   # table_name for create sql statements
my $table_no_quotes="";   # table_name for create sql statements
my $sl = '^\s+\w+\s+';  # matches the column name
my $tables_first_timestamp_column= 1;  #  decision to print warnings about default_timestamp not being in postgres
my $mysql_numeric_datatypes = "TINYINT|SMALLINT|MEDIUMINT|INT|INTEGER|BIGINT|REAL|DOUBLE|FLOAT|DECIMAL|NUMERIC";
my $mysql_datetime_datatypes = "|DATE|TIME|TIMESTAMP|DATETIME|YEAR";
my $mysql_text_datatypes = "CHAR|VARCHAR|BINARY|VARBINARY|TINYBLOB|BLOB|MEDIUMBLOB|LONGBLOB|TINYTEXT|TEXT|MEDIUMTEXT|LONGTEXT|ENUM|SET";
my $mysql_datatypesStr =  $mysql_numeric_datatypes . "|". $mysql_datetime_datatypes . "|". $mysql_text_datatypes ;
# handling INSERT INTO statements
my $rowRe = qr{
    \(                  # opening parens
        (               #  (start capture)
            (?:         #  (start group)
            '           # string start
                [^'\\]*     # up to string-end or backslash (escape)
                (?:     #  (start group)
                \\.     # gobble escaped character
                [^'\\]*     # up to string-end of backslash
                )*      #  (end group, repeat zero or more)
            '           # string end
            |           #  (OR)
            .*?         # everything else (not strings)
            )*          #  (end group, repeat zero or more)
        )               #  (end capture)
    \)                  # closing parent
}x;

my ($insert_table, $valueString);
#
########################################################
# 2.  subroutines
#
# get_identifier
# print_post_create_sql()
# quote_and_lc()
# make_plpgsql($table,$column_name) -- at end of file
########################################################

# returns an identifier with the given suffix doing controlled
# truncation if necessary
sub get_identifier($$$) {
    my ($table, $col, $suffix) = @_;
    my $name = '';
    $table=~s/\"//g; # make sure that $table doesn't have quotes so we don't end up with redundant quoting
    # in the case of multiple columns
    my @cols = split(/,/,$col);
    $col =~ s/,//g;
    # in case all columns together too long we have to truncate them
    if (length($col) > 55) {
        my $totaltocut = length($col)-55;
        my $tocut = ceil($totaltocut / @cols);
        @cols = map {substr($_,0,abs(length($_)-$tocut))} @cols;
        $col="";
        foreach (@cols){
            $col.=$_;
        }
    }

    my $max_table_length = 63 - length("_${col}_$suffix");

    if (length($table) > $max_table_length) {
        $table = substr($table, length($table) - $max_table_length, $max_table_length);
    }
    return quote_and_lc("${table}_${col}_${suffix}");
}


#
#
# called when we encounter next CREATE TABLE statement
# also called at EOF to print out for last table
# prints comments, indexes, foreign key constraints (the latter 2 possibly to a separate file)
sub print_post_create_sql() {
    my ( @create_idx_comments_constraints_commandsArr, $stmts, $table_field_combination);
    my %stmts;
    # loop to check for duplicates in $post_create_sql
    # Needed because of duplicate key declarations ( PRIMARY KEY and KEY), auto_increment columns

    @create_idx_comments_constraints_commandsArr = split(';\n?', $post_create_sql);
    if ($SEP_FILE) {
        open(SEP_FILE, ">>:encoding($ENC_OUT)", $SEP_FILE) or die "Unable to open $SEP_FILE for output: $!\n";
    }

    foreach (@create_idx_comments_constraints_commandsArr) {
        if (m/CREATE INDEX "*(\S+)"*\s/i) {  #  CREATE INDEX korean_english_wordsize_idx ON korean_english USING btree  (wordsize);
            $table_field_combination =  $1;
            # if this particular table_field_combination was already used do not print the statement:
            if ($SEP_FILE) {
                print SEP_FILE "$_;\n" if !defined($stmts{$table_field_combination});
            } else {
                print OUT "$_;\n" if !defined($stmts{$table_field_combination});
            }
            $stmts{$table_field_combination} = 1;
        }
        elsif (m/COMMENT/i) {  # COMMENT ON object IS 'text'; but comment may be part of table name so use 'elsif'
            print OUT "$_;\n"
        } else {  # foreign key constraint  or comments (those preceded by -- )
            if ($SEP_FILE) {
                print SEP_FILE "$_;\n";
            } else {
                print OUT "$_;\n"
            }
        }
    }

    if ($SEP_FILE) {
        close SEP_FILE;
    }
    $post_create_sql='';
    # empty %constraints for next " create table" statement
}

# quotes a string or a multicolumn string (comma separated)
# and optionally lowercase (if LOWERCASE is set)
# lowercase .... if user wants default postgres behavior
# quotes .... to preserve keywords and to preserve case when case-sensitive tables are to be used
sub quote_and_lc($)
{
    my $col = shift;
    if ($LOWERCASE) {
        $col = lc($col);
    }
    if ($col =~ m/,/) {
        my @cols = split(/,\s?/, $col);
        @cols = map {"\"$_\""} @cols;
        return join(', ', @cols);
    } else {
        return "\"$col\"";
    }
}

########################################################
# 3.  get commandline options and maybe print help
########################################################

GetOptions("help", "debug"=> \$opt_debug, "schema=s" => \$SCHEMA, "preserve_case" => \$opt_preserve_case, "char2varchar" => \$opt_char2varchar, "nodrop" => \$opt_nodrop, "sepfile=s" => \$opt_sepfile, "enc_in=s" => \$opt_enc_in, "enc_out=s" => \$opt_enc_out );

$HELP = $opt_help || 0;
$DEBUG = $opt_debug || 0;
$PRESERVE_CASE = $opt_preserve_case || 0;
if ($PRESERVE_CASE == 1) { $LOWERCASE = 0; }
else { $LOWERCASE = 1; }
$CHAR2VARCHAR = $opt_char2varchar || 0;
$NODROP = $opt_nodrop || 0;
$SEP_FILE = $opt_sepfile || 0;
$ENC_IN = $opt_enc_in || 'utf8';
$ENC_OUT = $opt_enc_out || 'utf8';

if (($HELP) || ! defined($ARGV[0]) || ! defined($ARGV[1])) {
    print "\n\nUsage: perl $0 {--help --debug --preserve_case --char2varchar --nodrop --schema --sepfile --enc_in --enc_out } mysql.sql pg.sql\n";
    print "\t* OPTIONS WITHOUT ARGS\n";
    print "\t--help:  prints this message \n";
    print "\t--debug: output the commented-out mysql line above the postgres line in pg.sql \n";
    print "\t--preserve_case: prevents automatic case-lowering of column and table names\n";
    print "\t\tIf you want to preserve case, you must set this flag. For example,\n";
    print "\t\tIf your client application quotes table and column-names and they have cases in them, set this flag\n";
    print "\t--char2varchar: converts all char fields to varchar\n";
    print "\t--nodrop: strips out DROP TABLE statements\n";
    print "\t\totherise harmless warnings are printed by psql when the dropped table does not exist\n";
    print "\n\t* OPTIONS WITH ARGS\n";
    print "\t--schema: outputs a line into the postgres sql file setting search_path \n";
    print "\t--sepfile: output foreign key constraints and indexes to a separate file so that it can be\n";
    print "\t\timported after large data set is inserted from another dump file\n";
    print "\t--enc_in: encoding of mysql in file (default utf8) \n";
    print "\t--enc_out: encoding of postgres out file (default utf8) \n";
    print "\n\t* REQUIRED ARGUMENTS\n";
    if (defined ($ARGV[0])) {
        print "\tmysql.sql ($ARGV[0])\n";
    } else {
        print "\tmysql.sql (undefined)\n";
    }
    if (defined ($ARGV[1])) {
        print "\tpg.sql ($ARGV[1])\n";
    } else {
        print "\tpg.sql (undefined)\n";
    }
    print "\n";
    exit 1;
}
########################################################
# 4.  process through mysql_dump.sql file
# in a big loop
########################################################

# open in and out files
open(IN,"<:encoding($ENC_IN)", $ARGV[0]) || die "can't open mysql dump file $ARGV[0]";
open(OUT,">:encoding($ENC_OUT)", $ARGV[1]) || die "can't open pg dump file $ARGV[1]";

# output header
print OUT "--\n";
print OUT "-- Generated from mysql2pgsql.perl\n";
print OUT "-- http://gborg.postgresql.org/project/mysql2psql/\n";
print OUT "-- (c) 2001 - 2007 Jose M. Duarte, Joseph Speigle\n";
print OUT "--\n";
print OUT "\n";
print OUT "-- warnings are printed for drop tables if they do not exist\n";
print OUT "-- please see http://archives.postgresql.org/pgsql-novice/2004-10/msg00158.php\n\n";
print OUT "-- ##############################################################\n";

if ($SCHEMA ) {
    print OUT "set search_path='" . $SCHEMA . "'\\g\n" ;
}

# loop through mysql file  on a per-line basis
while(<IN>) {

##############     flow     #########################
# (the lines are directed to different string variables at different times)
#
# handle drop table , unlock, connect statements
# if ( start of create table)   {
#   print out post_create table (indexes, foreign key constraints, comments from previous table)
#   add drop table statement if !$NODROP to pre_create_sql
#   next;
# }
# else if ( inside create table) {
#   add comments in this portion to create_sql
#   if ( end of create table) {
#      delete mysql-unique CREATE TABLE commands
#      print pre_create_sql
#      print the constraint tables for set and year datatypes
#      print create_sql
#      print function_create_sql (this is for the enum columns only)
#      next;
#   }
#   do substitutions
#    -- NUMERIC DATATYPES
#    -- CHARACTER DATATYPES
#    -- DATE AND TIME DATATYPES
#    -- KEY AND UNIQUE CREATIONS
#    and append them to create_sql
# } else {
#   print inserts on-the-spot (this script only changes default timestamp of 0000-00-00)
# }
# LOOP until EOF
#
########################################################


if (!/^\s*insert into/i) { # not inside create table so don't worry about data corruption
    s/`//g;  #  '`pgsql uses no backticks to denote table name (CREATE TABLE `sd`) or around field
            # and table names like  mysql
            # doh!  we hope all dashes and special chars are caught by the regular expressions :)
}
if (/^\s*USE\s*([^;]*);/) {
    print OUT "\\c ". $1;
    next;
}
if (/^(UN)?LOCK TABLES/i  || /drop\s+table/i ) {

    # skip
    # DROP TABLE is added when we see the CREATE TABLE
    next;
}
if (/(create\s+table\s+)([-_\w]+)\s/i) { #  example: CREATE TABLE `english_english`
    print_post_create_sql();   # for last table
    $tables_first_timestamp_column= 1;  #  decision to print warnings about default_timestamp not being in postgres
    $create_sql = '';
    $table_no_quotes = $2 ;
    $table=quote_and_lc($2);
    if ( !$NODROP )  {  # always print drop table if user doesn't explicitly say not to
        #  to drop a table that is referenced by a view or a foreign-key constraint of another table,
        #  CASCADE must be specified. (CASCADE will remove a dependent view entirely, but in the
        #  in the foreign-key case it will only remove the foreign-key constraint, not the other table entirely.)
        #  (source: 8.1.3 docs, section "drop table")
        warn "table $table will be dropped CASCADE\n";
        $pre_create_sql .= "DROP TABLE $table CASCADE;\n";    # custom dumps may be missing the 'dump' commands
    }

    s/(create\s+table\s+)([-_\w]+)\s/$1 $table /i;
    if ($DEBUG) {
        $create_sql .=  '-- ' . $_;
    }
    $create_sql .= $_;
    next;
}
if ($create_sql ne "") {         # we are inside create table statement so lets process datatypes
    # print out comments or empty lines in context
    if ($DEBUG) {
        $create_sql .=  '-- ' . $_;
    }
    if (/^#/ || /^$/ || /^\s*--/) {
        s/^#/--/;   #  Two hyphens (--) is the SQL-92 standard indicator for comments
        $create_sql.=$_;
        next;
    }

    if (/\).*;/i) {    # end of create table squence

        s/INSERT METHOD[=\s+][^;\s]+//i;
        s/PASSWORD=[^;\s]+//i;
        s/ROW_FORMAT=(?:DEFAULT|DYNAMIC|FIXED|COMPRESSED|REDUNDANT|COMPACT)+//i;
        s/KEY_BLOCK_SIZE=8//i;
        s/DELAY KEY WRITE=[^;\s]+//i;
        s/INDEX DIRECTORY[=\s+][^;\s]+//i;
        s/DATA DIRECTORY=[^;\s]+//i;
        s/CONNECTION=[^;\s]+//i;
        s/CHECKSUM=[^;\s]+//i;
        s/Type=[^;\s]+//i; # ISAM ,   # older versions
        s/COLLATE=[^;\s]+//i;         # table's collate
        s/COLLATE\s+[^;\s]+//i;         # table's collate
        # possible AUTO_INCREMENT starting index, it is used in mysql 5.0.26, not sure since which version
        if (/AUTO_INCREMENT=(\d+)/i) {
        # should take < ----  ) ENGINE=MyISAM AUTO_INCREMENT=16 DEFAULT CHARSET=latin1;
        # and should ouput --->  CREATE SEQUENCE "rhm_host_info_id_seq" START WITH 16;
        my $start_value = $1;
        print $auto_increment_seq . "--\n";
        # print $pre_create_sql . "--\n";
        $pre_create_sql =~ s/(CREATE SEQUENCE $auto_increment_seq )/$1 START WITH $start_value /;
    }
        s/AUTO_INCREMENT=\d+//i;
        s/PACK_KEYS=\d//i;            # mysql 5.0.22
        s/DEFAULT CHARSET=[^;\s]+//i; #  my mysql version is 4.1.11
        s/ENGINE\s*=\s*[^;\s]+//i;   #  my mysql version is 4.1.11
        s/ROW_FORMAT=[^;\s]+//i;   #  my mysql version is 5.0.22
        s/KEY_BLOCK_SIZE=8//i; 
        s/MIN_ROWS=[^;\s]+//i;
        s/MAX_ROWS=[^;\s]+//i;
        s/AVG_ROW_LENGTH=[^;\s]+//i;
        if (/COMMENT='([^']*)'/) {  # ) ENGINE=MyISAM DEFAULT CHARSET=utf8 COMMENT='must be country zones';
            $post_create_sql.="COMMENT ON TABLE $table IS '$1'\;"; # COMMENT ON table_name IS 'text';
            s/COMMENT='[^']*'//i;
        }
        $create_sql =~ s/,$//g;    # strip last , inside create table
        # make sure we end in a comma, as KEY statments are turned
        # into post_create_sql indices
        # they often are the last line so leaving a 'hanging comma'
        my @array = split("\n", $create_sql);
        for (my $a = $#array; $a >= 0; $a--) {  #loop backwards
            if ($a == $#array  && $array[$a] =~ m/,\s*$/) {    # for last line
                $array[$a] =~ s/,\s*$//;
                next;
            }
            if ($array[$a] !~ m/create table/i) {  # i.e. if there was more than one column in table
                if ($a != $#array  && $array[$a] !~ m/,\s*$/  ) {  # for second to last
                    $array[$a] =~ s/$/,/;
                    last;
                }
                elsif ($a != $#array  && $array[$a] =~ m/,\s*$/ ) {  # for second to last
                    last;
                }
            }
        }
        $create_sql = join("\n", @array) . "\n";
        $create_sql .=  $_;

        # put comments out first
        print OUT $pre_create_sql;

        # create separate table to reference and to hold mysql's possible set data-type
        # values.  do that table's creation before create table
        # definition
        foreach $column_name (keys %constraints) {
            $type=$constraints{$column_name}{'type'};
            $column_valuesStr = $constraints{$column_name}{'values'};
            $constraint_table_name = get_identifier(${table},${column_name} ,"constraint_table");
            if ($type eq 'set') {
                print OUT qq~DROP TABLE $constraint_table_name  CASCADE\\g\n~ ;
                print OUT qq~create table $constraint_table_name  ( set_values varchar UNIQUE)\\g\n~ ;
                $function_create_sql .= make_plpgsql($table,$column_name);
            } elsif ($type eq 'year')  {
                print OUT qq~DROP TABLE $constraint_table_name  CASCADE\\g\n~ ;
                print OUT qq~create table $constraint_table_name  ( year_values varchar UNIQUE)\\g\n~ ;
            }
            @column_values = split /,/, $column_valuesStr;
            foreach $value (@column_values) {
                print OUT qq~insert into $constraint_table_name   values (  $value  )\\g\n~; # ad ' for ints and varchars
            }
        }

        $create_sql =~ s/double double/double precision/g;

        # print create table and reset create table vars
        # when moving from each "create table" to "insert" part of dump
        print OUT $create_sql;
        print OUT $function_create_sql;
        $pre_create_sql="";
        $auto_increment_seq="";
        $create_sql="";
        $function_create_sql='';
        %constraints=();
        # the post_create_sql for this table is output at the beginning of the next table def
        # in case we want to make indexes after doing inserting
        next;
    }
    if (/^\s*(\w+)\s+.*COMMENT\s*'([^']*)'/) {  #`zone_country_id` int(11) COMMENT 'column comment here',
        $quoted_column=quote_and_lc($1);
        $post_create_sql.="COMMENT ON COLUMN $table"."."." $quoted_column IS '$2'\;"; # COMMENT ON table_name.column_name IS 'text';
        s/COMMENT\s*'[^']*'//i;
    }


    # NUMERIC DATATYPES
    #
    # auto_increment -> sequences
    # UNSIGNED conversions
    # TINYINT
    # SMALLINT
    # MEDIUMINT
    # INT, INTEGER
    # BIGINT
    #
    # DOUBLE [PRECISION], REAL
    # DECIMAL(M,D), NUMERIC(M,D)
    # FLOAT(p)
    # FLOAT

    s/(\w*int)\(\d+\)/$1/g;  # hack of the (n) stuff for e.g. mediumint(2) int(3)

    if (/^(\s*)(\w+)\s*.*numeric.*auto_increment/i) {         # int,auto_increment -> serial
        $seq = get_identifier($table, $2, 'seq');
        $quoted_column=quote_and_lc($2);
        # Smash datatype to int8 and autogenerate the sequence.
        s/^(\s*)(\w+)\s*.*NUMERIC(.*)auto_increment([^,]*)/$1 $quoted_column serial8 $4/ig;
        $create_sql.=$_;
        next;
    }
    if (/^\s*(\w+)\s+.*int.*auto_increment/i) {  #  example: data_id mediumint(8) unsigned NOT NULL auto_increment,
        $seq = get_identifier($table, $1, 'seq');
        $quoted_column=quote_and_lc($1);
        s/(\s*)(\w+)\s+.*int.*auto_increment([^,]*)/$1 $quoted_column serial8 $3/ig;
        $create_sql.=$_;
        next;
    }




    # convert UNSIGNED to CHECK constraints
    if (m/^(\s*)(\w+)\s+((float|double precision|double|real|decimal|numeric))(.*)unsigned/i) {
        $quoted_column = quote_and_lc($2);
        s/^(\s*)(\w+)\s+((float|double precision|double|real|decimal|numeric))(.*)unsigned/$1 $quoted_column $3 $4 CHECK ($quoted_column >= 0)/i;
    }
    # example:  `wordsize` tinyint(3) unsigned default NULL,
    if (m/^(\s+)(\w+)\s+(\w+)\s+unsigned/i) {
        $quoted_column=quote_and_lc($2);
        s/^(\s+)(\w+)\s+(\w+)\s+unsigned/$1 $quoted_column $3 CHECK ($quoted_column >= 0)/i;
    }
    if (m/^(\s*)(\w+)\s+(bigint.*)unsigned/) {
        $quoted_column=quote_and_lc($2);
        #  see http://archives.postgresql.org/pgsql-general/2005-07/msg01178.php
        #  and see http://www.postgresql.org/docs/8.2/interactive/datatype-numeric.html
        # see  http://dev.mysql.com/doc/refman/5.1/en/numeric-types.html  max size == 20 digits
        s/^(\s*)(\w+)\s+bigint(.*)unsigned/$1 $quoted_column NUMERIC (20,0) CHECK ($quoted_column >= 0)/i;

    }

    # int type conversion
    # TINYINT    (signed) -128 to 127 (unsigned) 0   255
    #  SMALLINT A small integer. The signed range is -32768 to 32767. The unsigned range is 0 to 65535.
    #  MEDIUMINT  A medium-sized integer. The signed range is -8388608 to 8388607. The unsigned range is 0 to 16777215.
    #  INT A normal-size integer. The signed range is -2147483648 to 2147483647. The unsigned range is 0 to 4294967295.
    # BIGINT The signed range is -9223372036854775808 to 9223372036854775807. The unsigned range is 0 to 18446744073709551615
    # for postgres see http://www.postgresql.org/docs/8.2/static/datatype-numeric.html#DATATYPE-INT
    s/^(\s+"*\w+"*\s+)tinyint/$1 smallint/i;
    s/^(\s+"*\w+"*\s+)mediumint/$1 integer/i;

    # the floating point types
    #   double -> double precision
    #   double(n,m) -> double precision
    #   float - no need for conversion
    #   float(n) - no need for conversion
    #   float(n,m) -> double precision

    s/(^\s*\w+\s+)double(\(\d+,\d+\))?/$1float/i;
    s/float(\(\d+,\d+\))/float/i;

    #
    # CHARACTER TYPES
    #
    # set
    # enum
    # binary(M), VARBINARy(M), tinyblob, tinytext,
    # bit
    # char(M), varchar(M)
    # blob -> text
    # mediumblob
    # longblob, longtext
    # text -> text
    # mediumtext
    # longtext
    #  mysql docs: A BLOB is a binary large object that can hold a variable amount of data.

    # set
    # For example, a column specified as SET('one', 'two') NOT NULL can have any of these values:
    # ''
    # 'one'
    # 'two'
    # 'one,two'
    if (/(\w*)\s+set\(((?:['"]\w+['"]\s*,*)+(?:['"]\w+['"])*)\)(.*)$/i) { # example:  `au_auth` set('r','w','d') NOT NULL default '',
        $column_name = $1;
        $constraints{$column_name}{'values'} = $2;  # 'abc','def', ...
        $constraints{$column_name}{'type'} = "set";  # 'abc','def', ...
        $_ =  qq~ $column_name varchar , ~;
        $column_name = quote_and_lc($1);
        $create_sql.=$_;
        next;

    }
    if (/(\S*)\s+enum\(((?:['"][^'"]+['"]\s*,)+['"][^'"]+['"])\)(.*)$/i) { # enum handling
        #  example:  `test` enum('?','+','-') NOT NULL default '?'
        # $2  is the values of the enum 'abc','def', ...
        $quoted_column=quote_and_lc($1);
        #  "test" NOT NULL default '?' CONSTRAINT test_test_constraint CHECK ("test" IN ('?','+','-'))
        $_ = qq~ $quoted_column varchar CHECK ($quoted_column IN ( $2 ))$3\n~;  # just assume varchar?
        $create_sql.=$_;
        next;
    }
    # Take care of "binary" option for char and varchar
    # (pre-4.1.2, it indicated a byte array; from 4.1.2, indicates
    # a binary collation)
    s/(?:var)?char(?:\(\d+\))? (?:byte|binary)/text/i;
    if (m/(?:var)?binary\s*\(\d+\)/i) {   #  c varBINARY(3) in Mysql
        warn "WARNING in table '$table' '$_':  binary type is converted to bytea (unsized) for Postgres\n";
    }
    s/(?:var)?binary(?:\(\d+\))?/text/i;   #  c varBINARY(3) in Mysql
    s/bit(?:\(\d+\))?/bytea/i;   #  bit datatype -> bytea

    # large datatypes
    s/\w*blob/bytea/gi;
    s/tinytext/text/gi;
    s/mediumtext/text/gi;
    s/longtext/text/gi;

    # char -> varchar -- if specified as a command line option
    # PostgreSQL would otherwise pad with spaces as opposed
    # to MySQL! Your user interface may depend on this!
    if ($CHAR2VARCHAR) {
        s/(^\s+\S+\s+)char/${1}varchar/gi;
    }

    # nuke column's collate and character set
    s/(\S+)\s+character\s+set\s+\w+/$1/gi;
    s/(\S+)\s+collate\s+\w+/$1/gi;

    #
    # DATE AND TIME TYPES
    #
    # date  time
    # year
    # datetime
    # timestamp

    # date  time
    # these are the same types in postgres, just do the replacement of 0000-00-00 date

    if (m/default '(\d+)-(\d+)-(\d+)([^']*)'/i) { # we grab the year, month and day
        # NOTE: times of 00:00:00 are possible and are okay
        my $time = '';
        my $year=$1;
        my $month= $2;
        my $day = $3;
        if ($4) {
            $time = $4;
        }
        if ($year eq "0000") { $year = '1970'; }
        if ($month eq "00") { $month = '01'; }
        if ($day eq "00") { $day = '01'; }
        s/default '[^']+'/default '$year-$month-$day$time'/i; # finally we replace with $datetime
    }

    # convert mysql's year datatype to a constraint
    if (/(\w*)\s+year\(4\)(.*)$/i) { # can be integer OR string 1901-2155
        $constraint_table_name = get_identifier($table,$1 ,"constraint_table");
        $column_name=quote_and_lc($1);
        @year_holder = ();
        $year='';
        for (1901 .. 2155) {
                $year = "'$_'";
            unless ($year =~ /2155/) { $year .= ','; }
             push( @year_holder, $year);
        }
        $constraints{$column_name}{'values'} = join('','',@year_holder);   # '1901','1902', ...
        $constraints{$column_name}{'type'} = "year";
        $_ =  qq~ $column_name varchar CONSTRAINT ${table}_${column_name}_constraint REFERENCES $constraint_table_name ("year_values") $2\n~;
        $create_sql.=$_;
        next;
    } elsif (/(\w*)\s+year\(2\)(.*)$/i) { # same for a 2-integer string
        $constraint_table_name = get_identifier($table,$1 ,"constraint_table");
        $column_name=quote_and_lc($1);
        @year_holder = ();
        $year='';
        for (1970 .. 2069) {
            $year = "'$_'";
            if ($year =~ /2069/) { next; }
            push( @year_holder, $year);
        }
        push( @year_holder, '0000');
        $constraints{$column_name}{'values'} = join(',',@year_holder);   # '1971','1972', ...
        $constraints{$column_name}{'type'} = "year";  # 'abc','def', ...
        $_ =  qq~ $1 varchar CONSTRAINT ${table}_${column_name}_constraint REFERENCES $constraint_table_name ("year_values") $2\n~;
        $create_sql.=$_;
        next;
    }

    # datetime
    # Default on a dump from MySQL 5.0.22 is in the same form as datetime so let it flow down
    # to the timestamp section and deal with it there
    s/(${sl})datetime /$1timestamp without time zone /i;

    # change not null datetime field to null valid ones
    # (to support remapping of "zero time" to null
    # s/($sl)datetime not null/$1timestamp without time zone/i;


    # timestamps
    #
    # nuke datetime representation (not supported in PostgreSQL)
    # change default time of 0000-00-00 to 1970-01-01

    # we may possibly need to create a trigger to provide
    # equal functionality with ON UPDATE CURRENT TIMESTAMP


    if (m/${sl}timestamp/i) {
        if ( m/ON UPDATE CURRENT_TIMESTAMP/i )  {  # the ... default CURRENT_TIMESTAMP  only applies for blank inserts, not updates
            s/ON UPDATE CURRENT_TIMESTAMP//i ;
            m/^\s*(\w+)\s+timestamp/i ;
            # automatic trigger creation
            $table_no_quotes =~ s/"//g;
$function_create_sql .= " CREATE OR REPLACE FUNCTION update_". $table_no_quotes . "() RETURNS trigger AS '
BEGIN
    NEW.$1 := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
' LANGUAGE 'plpgsql';

-- before INSERT is handled by 'default CURRENT_TIMESTAMP'
CREATE TRIGGER add_current_date_to_".$table_no_quotes." BEFORE UPDATE ON ". $table . " FOR EACH ROW EXECUTE PROCEDURE
update_".$table_no_quotes."();\n";

        }
        if ($tables_first_timestamp_column && m/DEFAULT NULL/i) {
            # DEFAULT NULL is the same as DEFAULT CURRENT_TIMESTAMP for the first TIMESTAMP  column. (MYSQL manual)
            s/($sl)(timestamp\s+)default null/$1 $2 DEFAULT CURRENT_TIMESTAMP/i;
        }
        $tables_first_timestamp_column= 0;
        if (m/${sl}timestamp\s*\(\d+\)/i) {   # fix for timestamps with width spec not handled (ID: 1628)
            warn "WARNING for in table '$table' '$_': your default timestamp width is being ignored for table $table \n";
            s/($sl)timestamp(?:\(\d+\))/$1datetime/i;
        }
    } # end timestamp section

    # KEY AND UNIQUE CREATIONS
    #
    # unique
    if ( /^\s+unique\s+\(([^(]+)\)/i ) { #  example    UNIQUE `name` (`name`), same as UNIQUE KEY
        #  POSTGRESQL:  treat same as mysql unique
        $quoted_column = quote_and_lc($1);
        s/\s+unique\s+\(([^(]+)\)/ unique ($quoted_column) /i;
            $create_sql.=$_;
        next;
        } elsif ( /^\s+unique\s+key\s*(\w+)\s*\(([^(]+)\)/i ) { #  example    UNIQUE KEY `name` (`name`)
            #  MYSQL: unique  key: allows null=YES, allows duplicates=NO (*)
            #  ... new ... UNIQUE KEY `unique_fullname` (`fullname`)  in my mysql v. Ver 14.12 Distrib 5.1.7-beta
            #  POSTGRESQL:  treat same as mysql unique
        # just quote columns
        $quoted_column = quote_and_lc($2);
            s/\s+unique\s+key\s*(\w+)\s*\(([^(]+)\)/ unique ($quoted_column) /i;
            $create_sql.=$_;
        # the index corresponding to the 'key' is automatically created
            next;
    }
    # keys
    if ( /^\s+fulltext key\s+/i) { # example:  FULLTEXT KEY `commenttext` (`commenttext`)
    # that is key as a word in the first check for a match
        # the tsvector datatype is made for these types of things
        # example mysql file:
        #  what is tsvector datatype?
        #  http://www.sai.msu.su/~megera/postgres/gist/tsearch/V2/docs/tsearch-V2-intro.html
        warn "dba must do fulltext key transformation for $table\n";
        next;
    }
    if ( /^(\s+)constraint (\S+) foreign key \((\S+)\) references (\S+) \((\S+)\)(.*)/i ) {
        $quoted_column =quote_and_lc($3);
        $col=quote_and_lc($5);
        $post_create_sql .= "ALTER TABLE $table ADD FOREIGN KEY ($quoted_column) REFERENCES " . quote_and_lc($4) . " ($col);\n";
        next;
    }
    if ( /^\s*primary key\s*\(([^)]+)\)([,\s]+)/i ) { #  example    PRIMARY KEY (`name`)
        # MYSQL: primary key: allows null=NO , allows duplicates=NO
        #  POSTGRESQL: When an index is declared unique, multiple table rows with equal indexed values will not be
        #       allowed. Null values are not considered equal.
        #  POSTGRESQL quote's source: 8.1.3 docs section 11.5 "unique indexes"
        #  so, in postgres, we need to add a NOT NULL to the UNIQUE constraint
        # and, primary key (mysql) == primary key (postgres) so that we *really* don't need change anything
        $quoted_column = quote_and_lc($1);
        s/(\s*)primary key\s+\(([^)]+)\)([,\s]+)/$1 primary key ($quoted_column)$3/i;
        # indexes are automatically created for unique columns
        $create_sql.=$_;
        next;
    } elsif (m/^\s+key\s[-_\s\w]+\((.+)\)/i    ) {     # example:   KEY `idx_mod_english_def_word` (`word`),
        # regular key: allows null=YES, allows duplicates=YES
        # MYSQL:   KEY is normally a synonym for INDEX.  http://dev.mysql.com/doc/refman/5.1/en/create-table.html
        #
        #  * MySQL: ALTER TABLE {$table} ADD KEY $column ($column)
        #  * PostgreSQL: CREATE INDEX {$table}_$column_idx ON {$table}($column) // Please note the _idx "extension"
        #    PRIMARY KEY (`postid`),
        #    KEY `ownerid` (`ownerid`)
        # create an index for everything which has a key listed for it.
        my $col = $1;
        # TODO we don't have a translation for the substring syntax in text columns in MySQL (e.g. "KEY my_idx (mytextcol(20))")
        # for now just getting rid of the brackets and numbers (the substring specifier):
        $col=~s/\(\d+\)//g;
        $quoted_column = quote_and_lc($col);
        if ($col =~ m/,/) {
            $col =  s/,/_/;
        }
        $index = get_identifier($table, $col, 'idx');
        $post_create_sql.="CREATE INDEX $index ON $table USING btree ($quoted_column)\;";
        # just create index do not add to create table statement
        next;
    }

    # handle 'key' declared at end of column
    if (/\w+.*primary key/i) {   # mysql: key is normally just a synonym for index
    # just leave as is ( postgres has primary key type)


    } elsif (/(\w+\s+(?:$mysql_datatypesStr)\s+.*)key/i) {   # mysql: key is normally just a synonym for index
    # I can't find a reference for 'key' in a postgres command without using the word 'primary key'
        s/$1key/$1/i ;
        $index = get_identifier($table, $1, 'idx');
        $quoted_column =quote_and_lc($1);
        $post_create_sql.="CREATE INDEX $index ON $table USING btree ($quoted_column) \;";
        $create_sql.=$_;
    }



    # do we really need this anymore?
    # remap colums with names of existing system attribute
    if (/"oid"/i) {
        s/"oid"/"_oid"/g;
        print STDERR "WARNING: table $table uses column \"oid\" which is renamed to \"_oid\"\nYou should fix application manually! Press return to continue.";
        my $wait=<STDIN>;
    }

    s/oid/_oid/i if (/key/i && /oid/i); # fix oid in key

    # FINAL QUOTING OF ALL COLUMNS
    # quote column names which were not already quoted
    # perhaps they were not quoted because they were not explicitly handled
    if (!/^\s*"(\w+)"(\s+)/i) {
        /^(\s*)(\w+)(\s+)(.*)$/i ;
        $quoted_column= quote_and_lc($2);
        s/^(\s*)(\w+)(\s+)(.*)$/$1 $quoted_column $3 $4 /;
    }
    $create_sql.=$_;
    #  END of if ($create_sql ne "") i.e. were inside create table statement so processed datatypes
}
# add "not in create table" comments or empty lines to pre_create_sql
elsif (/^#/ || /^$/ || /^\s*--/) {
    s/^#/--/;   #  Two hyphens (--) is the SQL-92 standard indicator for comments
    $pre_create_sql .=  $_ ;  # printed above create table statement
    next;
}
elsif (/^\s*insert into/i) { # not inside create table and doing insert
    # fix mysql's zero/null value for timestamps
    s/'0000-00-00/'1970-01-01/gi;
    # commented out to fix bug "Field contents interpreted as a timestamp", what was the point of this line anyway?
    #s/([12]\d\d\d)([01]\d)([0-3]\d)([0-2]\d)([0-6]\d)([0-6]\d)/'$1-$2-$3 $4:$5:$6'/;

    #---- fix data in inserted data: (from MS world)
    s!\x96!-!g;    # --
    s!\x93!"!g;    # ``
    s!\x94!"!g;    # ''
    s!\x85!... !g;    # \ldots
    s!\x92!`!g;

    print OUT $pre_create_sql;    # print comments preceding the insert section
    $pre_create_sql="";
    $auto_increment_seq = "";

    s/'((?:[^'\\]++|\\.)*+)'(?=[),])/E'$1'/g;
    # for the E'' see http://www.postgresql.org/docs/8.2/interactive/release-8-1.html
    s!\\\\!\\\\\\\\!g;      # replace \\ with ]\\\\

    # split 'extended' INSERT INTO statements to something PostgreSQL can  understand
    ( $insert_table,  $valueString) = $_ =~ m/^INSERT\s+INTO\s+['`"]*(.*?)['`"]*\s+VALUES\s*(.*)/i;
    $insert_table = quote_and_lc($insert_table);

    s/^INSERT INTO.*?\);//i;  # hose the statement which is to be replaced whether a run-on or not
    # guarantee table names are quoted
    print OUT qq(INSERT INTO $insert_table VALUES $valueString \n);

} else {
    print OUT $_ ;  #  example: /*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
}
#  keep looping and get next line of IN file

} # END while(<IN>)

print_post_create_sql();   # in case there is extra from the last table

#################################################################
#  5.  print_plgsql function prototype
#      emulate the set datatype with the following plpgsql function
#      looks ugly so putting at end of file
#################################################################
#
sub make_plpgsql {
my ($table,$column_name) = ($_[0],$_[1]);
$table=~s/\"//g; # make sure that $table doesn't have quotes so we don't end up with redundant quoting
my $constraint_table = get_identifier($table,$column_name ,"constraint_table");
return "
-- this function is called by the insert/update trigger
-- it checks if the INSERT/UPDATE for the 'set' column
-- contains members which comprise a valid mysql set
-- this TRIGGER function therefore acts like a constraint
--  provided limited functionality for mysql's set datatype
-- just verifies and matches for string representations of the set at this point
-- though the set datatype uses bit comparisons, the only supported arguments to our
-- set datatype are VARCHAR arguments
-- to add a member to the set add it to the ".$table."_".$column_name." table
CREATE OR REPLACE FUNCTION check_".$table."_".$column_name."_set(  ) RETURNS TRIGGER AS \$\$\n
DECLARE
----
arg_str VARCHAR ;
argx VARCHAR := '';
nobreak INT := 1;
rec_count INT := 0;
psn INT := 0;
str_in VARCHAR := NEW.$column_name;
----
BEGIN
----
IF str_in IS NULL THEN RETURN NEW ; END IF;
arg_str := REGEXP_REPLACE(str_in, '\\',\\'', ',');  -- str_in is CONSTANT
arg_str := REGEXP_REPLACE(arg_str, '^\\'', '');
arg_str := REGEXP_REPLACE(arg_str, '\\'\$', '');
-- RAISE NOTICE 'arg_str %',arg_str;
psn := POSITION(',' in arg_str);
IF psn > 0 THEN
    psn := psn - 1; -- minus-1 from comma position
    -- RAISE NOTICE 'psn %',psn;
    argx := SUBSTRING(arg_str FROM 1 FOR psn);  -- get one set member
    psn := psn + 2; -- go to first starting letter
    arg_str := SUBSTRING(arg_str FROM psn);   -- hack it off
ELSE
    psn := 0; -- minus-1 from comma position
    argx := arg_str;
END IF;
-- RAISE NOTICE 'argx %',argx;
-- RAISE NOTICE 'new arg_str: %',arg_str;
WHILE nobreak LOOP
    EXECUTE 'SELECT count(*) FROM $constraint_table WHERE set_values = ' || quote_literal(argx) INTO rec_count;
    IF rec_count = 0 THEN RAISE EXCEPTION 'one of the set values was not found';
    END IF;
    IF psn > 0 THEN
        psn := psn - 1; -- minus-1 from comma position
        -- RAISE NOTICE 'psn %',psn;
        argx := SUBSTRING(arg_str FROM 1 FOR psn);  -- get one set member
        psn := psn + 2; -- go to first starting letter
        arg_str := SUBSTRING(arg_str FROM psn);   -- hack it off
        psn := POSITION(',' in arg_str);
    ELSE nobreak = 0;
    END IF;
    -- RAISE NOTICE 'next argx % and next arg_str %', argx, arg_str;
END LOOP;
RETURN NEW;
----
END;
\$\$ LANGUAGE 'plpgsql' VOLATILE;

drop trigger set_test ON $table;
-- make a trigger for each set field
-- make trigger and hard-code in column names
-- see http://archives.postgresql.org/pgsql-interfaces/2005-02/msg00020.php
CREATE   TRIGGER    set_test
BEFORE   INSERT OR   UPDATE  ON $table   FOR  EACH  ROW
EXECUTE  PROCEDURE  check_".$table."_".$column_name."_set();\n";
} #  end sub make_plpgsql();

