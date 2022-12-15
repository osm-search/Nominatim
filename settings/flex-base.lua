-- Core functions for Nominatim import flex style.
--

local module = {}

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

function Place:clean(data)
    if data.delete ~= nil or data.extra ~= nil then
        for k, v in pairs(self.object.tags) do
            if data.delete ~= nil and data.delete(k, v) then
                self.object.tags[k] = nil
            elseif data.extra ~= nil and data.extra(k, v) then
                self.extratags[k] = v
                self.object.tags[k] = nil
            end
        end
    end
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

local function strip_address_prefix(k)
    if k:sub(1, 5) == 'addr:' then
        return k:sub(6)
    end

    if k:sub(1, 6) == 'is_in:' then
        return k:sub(7)
    end

    return k
end


function Place:grab_address_parts(data)
    local count = 0

    if data.groups ~= nil then
        for k, v in pairs(self.object.tags) do
            local atype = data.groups(k, v)

            if atype ~= nil then
                if atype == 'main' then
                    self.has_name = true
                    self.address[strip_address_prefix(k)] = v
                    count = count + 1
                elseif atype == 'extra' then
                    self.address[strip_address_prefix(k)] = v
                else
                    self.address[atype] = v
                end
                self.object.tags[k] = nil
            end
        end
    end

    return count
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

function Place:grab_name_parts(data)
    local fallback = nil

    if data.groups ~= nil then
        for k, v in pairs(self.object.tags) do
            local atype = data.groups(k, v)

            if atype ~= nil then
                self.names[k] = v
                if atype == 'main' then
                    self.has_name = true
                elseif atype == 'house' then
                    self.has_name = true
                    fallback = {'place', 'house', 'always'}
                end
            end
        end
    end

    return fallback
end

function Place:grab_tag(key)
    return self.object:grab_tag(key)
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


function module.tag_match(data)
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


function module.tag_group(data)
    if data == nil or next(data) == nil then
        return nil
    end

    local fullmatches = {}
    local key_prefixes = {}
    local key_suffixes = {}

    for group, tags in pairs(data) do
        for _, key in pairs(tags) do
            if key:sub(1, 1) == '*' then
                if #key > 1 then
                    if key_suffixes[#key - 1] == nil then
                        key_suffixes[#key - 1] = {}
                    end
                    key_suffixes[#key - 1][key:sub(2)] = group
                end
            elseif key:sub(#key, #key) == '*' then
                if key_prefixes[#key - 1] == nil then
                    key_prefixes[#key - 1] = {}
                end
                key_prefixes[#key - 1][key:sub(1, #key - 1)] = group
            else
                fullmatches[key] = group
            end
        end
    end

    return function (k, v)
        local val = fullmatches[k]
        if val ~= nil then
            return val
        end

        for slen, slist in pairs(key_suffixes) do
            if #k >= slen then
                val = slist[k:sub(-slen)]
                if val ~= nil then
                    return val
                end
            end
        end

        for slen, slist in pairs(key_prefixes) do
            if #k >= slen then
                val = slist[k:sub(1, slen)]
                if val ~= nil then
                    return val
                end
            end
        end
    end
end

-- Process functions for all data types
function osm2pgsql.process_node(object)

    local function geom_func(o)
        return o:as_point()
    end

    module.process_tags(Place.new(object, geom_func))
end

function osm2pgsql.process_way(object)

    local function geom_func(o)
        local geom = o:as_polygon()

        if geom:is_null() then
            geom = o:as_linestring()
        end

        return geom
    end

    module.process_tags(Place.new(object, geom_func))
end

function module.relation_as_multipolygon(o)
    return o:as_multipolygon()
end

function module.relation_as_multiline(o)
    return o:as_multilinestring():line_merge()
end

function osm2pgsql.process_relation(object)
    local geom_func = module.RELATION_TYPES[object.tags.type]

    if geom_func ~= nil then
        module.process_tags(Place.new(object, geom_func))
    end
end

function module.process_tags(o)
    o:clean{delete = module.PRE_DELETE, extra = module.PRE_EXTRAS}

    -- Exception for boundary/place double tagging
    if o.object.tags.boundary == 'administrative' then
        o:grab_extratags{match = function (k, v)
            return k == 'place' and v:sub(1,3) ~= 'isl'
        end}
    end

    -- name keys
    local fallback = o:grab_name_parts{groups=module.NAMES}

    -- address keys
    if o:grab_address_parts{groups=module.ADDRESS_TAGS} > 0 and fallback == nil then
        fallback = {'place', 'house', 'always'}
    end
    if o.address.country ~= nil and #o.address.country ~= 2 then
        o.address['country'] = nil
    end
    if fallback == nil and o.address.postcode ~= nil then
        fallback = {'place', 'postcode', 'always'}
    end

    if o.address.interpolation ~= nil then
        o:write_place('place', 'houses', 'always', module.SAVE_EXTRA_MAINS)
        return
    end

    o:clean{delete = module.POST_DELETE, extra = module.POST_EXTRAS}

    -- collect main keys
    for k, v in pairs(o.object.tags) do
        local ktype = module.MAIN_KEYS[k]
        if ktype == 'fallback' then
            if o.has_name then
                fallback = {k, v, 'named'}
            end
        elseif ktype ~= nil then
            o:write_place(k, v,module.MAIN_KEYS[k], module.SAVE_EXTRA_MAINS)
        end
    end

    if fallback ~= nil and o.num_entries == 0 then
        o:write_place(fallback[1], fallback[2], fallback[3], module.SAVE_EXTRA_MAINS)
    end
end

------ defaults --------------

module.RELATION_TYPES = {
    multipolygon = module.relation_as_multipolygon,
    boundary = module.relation_as_multipolygon,
    waterway = module.relation_as_multiline
}


return module
