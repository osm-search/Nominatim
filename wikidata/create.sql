DROP TABLE entity;
DROP TABLE entity_label;
DROP TABLE entity_description;
DROP TABLE entity_alias;
DROP TABLE entity_link;
DROP TABLE entity_property;

CREATE TABLE entity (
    entity_id           bigint,
    title               text,
    pid                 bigint,
    qid                 bigint,
    datatype            text,
    CONSTRAINT pk_entity PRIMARY KEY(entity_id)
);

CREATE TABLE entity_label  (
    entity_id           bigint,
    language            text,
    label               text,
    CONSTRAINT pk_entity_label PRIMARY KEY(entity_id,language)
);

CREATE TABLE entity_description  (
    entity_id           bigint,
    language            text,
    description         text,
    CONSTRAINT pk_entity_description PRIMARY KEY(entity_id,language)
);

CREATE TABLE entity_alias  (
    entity_id           bigint,
    language            text,
    alias               text,
    CONSTRAINT pk_entity_alias PRIMARY KEY(entity_id,language,alias)
);

CREATE TABLE entity_link  (
    entity_id           bigint,
    target              text,
    value               text,
    CONSTRAINT pk_entity_link PRIMARY KEY(entity_id,target)
);

CREATE TABLE entity_link_hit  (
    entity_id           bigint,
    target              text,
    value               text,
    hits		bigint,
    CONSTRAINT pk_entity_link_hit PRIMARY KEY(entity_id,target)
);

CREATE TABLE link_hit  (
    target              text,
    value               text,
    hits		bigint,
    CONSTRAINT pk_link_hit PRIMARY KEY(target,value)
);

CREATE TABLE entity_property  (
    entity_id           bigint,
    order_id            bigint,
    pid                 bigint,
    string              text,
    toqid               bigint,
    location            geometry,
    datetime		timestamp with time zone,
    CONSTRAINT pk_entity_property PRIMARY KEY(entity_id, order_id)
);

CREATE TABLE import_link_hit  (
    target              text,
    value               text,
    hits		bigint
);
