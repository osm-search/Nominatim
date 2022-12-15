-- Core functions for Nominatim import flex style.
--


-- The single place table.
place_table = osm2pgsql.define_table{
    name = "place",
    ids = { type = 'any', id_column = 'osm_id', type_column = 'osm_type' },
    columns = {
        { column = 'class', type = 'text', not_null = true },
        { column = 'type', type = 'text', not_null = true },
        { column = 'admin_level', type = 'smallint' },
        { column = 'name', type = 'hstore' },
        { column = 'address', type = 'hstore' },
        { column = 'extratags', type = 'hstore' },
        { column = 'geometry', type = 'geometry', projection = 'WGS84', not_null = true },
    },
    indexes = {}
}

------------- Place class ------------------------------------------

local Place = {}
Place.__index = Place

function Place.new(object, geom_func)
    local self = setmetatable({}, Place)
    self.object = object
    self.geom_func = geom_func

    self.admin_level = tonumber(self.object:grab_tag('admin_level'))
    if self.admin_level == nil
       or self.admin_level <= 0 or self.admin_level > 15
       or math.floor(self.admin_level) ~= self.admin_level then
        self.admin_level = 15
    end

    self.num_entries = 0
    self.has_name = false
    self.names = {}
    self.address = {}
    self.extratags = {}

    return self
end

function Place:delete(data)
    if data.match ~= nil then
        for k, v in pairs(self.object.tags) do
            if data.match(k, v) then
                self.object.tags[k] = nil
            end
        end
    end
end

function Place:grab_extratags(data)
    local count = 0

    if data.match ~= nil then
        for k, v in pairs(self.object.tags) do
            if data.match(k, v) then
                self.object.tags[k] = nil
                self.extratags[k] = v
                count = count + 1
            end
        end
    end

    return count
end

function Place:grab_address(data)
    local count = 0

    if data.match ~= nil then
        for k, v in pairs(self.object.tags) do
            if data.match(k, v) then
                self.object.tags[k] = nil

                if data.include_on_name == true then
                    self.has_name = true
                end

                if data.out_key ~= nil then
                    self.address[data.out_key] = v
                    return 1
                end

                if k:sub(1, 5) == 'addr:' then
                    self.address[k:sub(6)] = v
                elseif k:sub(1, 6) == 'is_in:' then
                    self.address[k:sub(7)] = v
                else
                    self.address[k] = v
                end
                count = count + 1
            end
        end
    end

    return count
end

function Place:set_address(key, value)
    self.address[key] = value
end

function Place:grab_name(data)
    local count = 0

    if data.match ~= nil then
        for k, v in pairs(self.object.tags) do
            if data.match(k, v) then
                self.object.tags[k] = nil
                self.names[k] = v
                if data.include_on_name ~= false then
                    self.has_name = true
                end
                count = count + 1
            end
        end
    end

    return count
end

function Place:grab_tag(key)
    return self.object:grab_tag(key)
end

function Place:tags()
    return self.object.tags
end

function Place:write_place(k, v, mtype, save_extra_mains)
    if mtype == nil then
        return 0
    end

    v = v or self.object.tags[k]
    if v == nil then
        return 0
    end

    if type(mtype) == 'table' then
        mtype = mtype[v] or mtype[1]
    end

    if mtype == 'always' or (self.has_name and mtype == 'named') then
        return self:write_row(k, v, save_extra_mains)
    end

    if mtype == 'named_with_key' then
        local names = {}
        local prefix = k .. ':name'
        for namek, namev in pairs(self.object.tags) do
            if namek:sub(1, #prefix) == prefix
               and (#namek == #prefix
                    or namek:sub(#prefix + 1, #prefix + 1) == ':') then
                names[namek:sub(#k + 2)] = namev
            end
        end

        if next(names) ~= nil then
            local saved_names = self.names
            self.names = names

            local results = self:write_row(k, v, save_extra_mains)

            self.names = saved_names

            return results
        end
    end

    return 0
end

function Place:write_row(k, v, save_extra_mains)
    if self.geometry == nil then
        self.geometry = self.geom_func(self.object)
    end
    if self.geometry:is_null() then
        return 0
    end

    if save_extra_mains then
        for extra_k, extra_v in pairs(self.object.tags) do
            if extra_k ~= k then
                self.extratags[extra_k] = extra_v
            end
        end
    end

    place_table:insert{
        class = k,
        type = v,
        admin_level = self.admin_level,
        name = next(self.names) and self.names,
        address = next(self.address) and self.address,
        extratags = next(self.extratags) and self.extratags,
        geometry = self.geometry
    }

    if save_extra_mains then
        for k, v in pairs(self.object.tags) do
            self.extratags[k] = nil
        end
    end

    self.num_entries = self.num_entries + 1

    return 1
end


function tag_match(data)
    if data == nil or next(data) == nil then
        return nil
    end

    local fullmatches = {}
    local key_prefixes = {}
    local key_suffixes = {}

    if data.keys ~= nil then
        for _, key in pairs(data.keys) do
            if key:sub(1, 1) == '*' then
                if #key > 1 then
                    if key_suffixes[#key - 1] == nil then
                        key_suffixes[#key - 1] = {}
                    end
                    key_suffixes[#key - 1][key:sub(2)] = true
                end
            elseif key:sub(#key, #key) == '*' then
                if key_prefixes[#key - 1] == nil then
                    key_prefixes[#key - 1] = {}
                end
                key_prefixes[#key - 1][key:sub(1, #key - 1)] = true
            else
                fullmatches[key] = true
            end
        end
    end

    if data.tags ~= nil then
        for k, vlist in pairs(data.tags) do
            if fullmatches[k] == nil then
                fullmatches[k] = {}
                for _, v in pairs(vlist) do
                    fullmatches[k][v] = true
                end
            end
        end
    end

    return function (k, v)
        if fullmatches[k] ~= nil and (fullmatches[k] == true or fullmatches[k][v] ~= nil) then
            return true
        end

        for slen, slist in pairs(key_suffixes) do
            if #k >= slen and slist[k:sub(-slen)] ~= nil then
                return true
            end
        end

        for slen, slist in pairs(key_prefixes) do
            if #k >= slen and slist[k:sub(1, slen)] ~= nil then
                return true
            end
        end

        return false
    end
end


-- Process functions for all data types
function osm2pgsql.process_node(object)

    local function geom_func(o)
        return o:as_point()
    end

    process_tags(Place.new(object, geom_func))
end

function osm2pgsql.process_way(object)

    local function geom_func(o)
        local geom = o:as_polygon()

        if geom:is_null() then
            geom = o:as_linestring()
        end

        return geom
    end

    process_tags(Place.new(object, geom_func))
end

function relation_as_multipolygon(o)
    return o:as_multipolygon()
end

function relation_as_multiline(o)
    return o:as_multilinestring():line_merge()
end

function osm2pgsql.process_relation(object)
    local geom_func = RELATION_TYPES[object.tags.type]

    if geom_func ~= nil then
        process_tags(Place.new(object, geom_func))
    end
end

function process_tags(o)
    local fallback

    o:delete{match = PRE_DELETE}
    o:grab_extratags{match = PRE_EXTRAS}

    -- Exception for boundary/place double tagging
    if o.object.tags.boundary == 'administrative' then
        o:grab_extratags{match = function (k, v)
            return k == 'place' and v:sub(1,3) ~= 'isl'
        end}
    end

    -- address keys
    o:grab_address{match=COUNTRY_TAGS, out_key='country'}
    if o.address.country ~= nil and #o.address.country ~= 2 then
        o.address['country'] = nil
    end
    if o:grab_name{match=HOUSENAME_TAGS} > 0 then
        fallback = {'place', 'house'}
    end
    if o:grab_address{match=HOUSENUMBER_TAGS, include_on_name = true} > 0 and fallback == nil then
        fallback = {'place', 'house'}
    end
    if o:grab_address{match=POSTCODES, out_key='postcode'} > 0 and fallback == nil then
        fallback = {'place', 'postcode'}
    end

    local is_interpolation = o:grab_address{match=INTERPOLATION_TAGS} > 0

    o:grab_address{match=ADDRESS_TAGS}

    if is_interpolation then
        o:write_place('place', 'houses', 'always', SAVE_EXTRA_MAINS)
        return
    end

    -- name keys
    o:grab_name{match = NAMES}
    o:grab_name{match = REFS, include_on_name = false}

    o:delete{match = POST_DELETE}
    o:grab_extratags{match = POST_EXTRAS}

    -- collect main keys
    local num_mains = 0
    for k, v in pairs(o:tags()) do
        num_mains = num_mains + o:write_place(k, v, MAIN_KEYS[k], SAVE_EXTRA_MAINS)
    end

    if num_mains == 0 then
        for tag, mtype in pairs(MAIN_FALLBACK_KEYS) do
            if o:write_place(tag, nil, mtype, SAVE_EXTRA_MAINS) > 0 then
                return
            end
        end

        if fallback ~= nil then
            o:write_place(fallback[1], fallback[2], 'always', SAVE_EXTRA_MAINS)
        end
    end
end


