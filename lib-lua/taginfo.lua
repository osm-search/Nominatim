-- Prints taginfo project description in the standard output
--

-- create fake "osm2pgsql" table for flex-base, originally created by the main C++ program
osm2pgsql = {}
function osm2pgsql.define_table(...) end

-- provide path to flex-style lua file
package.path = arg[0]:match("(.*/)") .. "?.lua;" .. package.path
local flex = require('import-' .. (arg[1] or 'extratags'))
local json = require ('dkjson')

local NAME_DESCRIPTIONS = {
    'Searchable auxiliary name of the place',
    main = 'Searchable primary name of the place',
    house = 'House name part of an address, searchable'
}
local ADDRESS_DESCRIPTIONS = {
    'Used to determine the address of a place',
    main = 'Primary key for an address point',
    postcode = 'Used to determine the postcode of a place',
    country = 'Used to determine country of a place (only if written as two-letter code)',
    interpolation = 'Primary key for an address interpolation line'
}

------------ helper functions ---------------------
-- Sets the key order for the resulting JSON table
local function set_keyorder(table, order)
    setmetatable(table, {
        __jsonorder = order
    })
end

local function get_key_description(key, description)
    local desc = {}
    desc.key = key
    desc.description = description
    set_keyorder(desc, {'key', 'description'})
    return desc
end

local function get_key_value_description(key, value, description)
    local desc = {key = key, value = value, description = description}
    set_keyorder(desc, {'key', 'value', 'description'})
    return desc
end

local function group_table_to_keys(tags, data, descriptions)
    for group, values in pairs(data) do
        local desc = descriptions[group] or descriptions[1]
        for _, key in pairs(values) do
            if key:sub(1, 1) ~= '*' and key:sub(#key, #key) ~= '*' then
                table.insert(tags, get_key_description(key, desc))
            end
        end
    end
end

-- Prints the collected tags in the required format in JSON
local function print_taginfo()
    local taginfo = flex.get_taginfo()
    local tags = {}

    for k, values in pairs(taginfo.main) do
        if values[1] == nil or values[1] == 'delete' or values[1] == 'extra' then
            for v, group in pairs(values) do
                if type(v) == 'string' and group ~= 'delete' and group ~= 'extra' then
                    local text = 'POI/feature in the search database'
                    if type(group) ~= 'function' then
                        text = 'Fallback ' .. text
                    end
                    table.insert(tags, get_key_value_description(k, v, text))
                end
            end
        elseif type(values[1]) == 'function' or values[1] == 'fallback' then
            local desc = 'POI/feature in the search database'
            if values[1] == 'fallback' then
                desc = 'Fallback ' .. desc
            end
            local excp = {}
            for v, group in pairs(values) do
                if group == 'delete' or group == 'extra' then
                    table.insert(excp, v)
                end
            end
            if next(excp) ~= nil then
                desc = desc .. string.format(' (except for values: %s)',
                                             table.concat(excp, ', '))
            end
            table.insert(tags, get_key_description(k, desc))
        end
    end

    group_table_to_keys(tags, taginfo.name, NAME_DESCRIPTIONS)
    group_table_to_keys(tags, taginfo.address, ADDRESS_DESCRIPTIONS)

    local format = {
        data_format = 1,
        data_url = 'https://nominatim.openstreetmap.org/taginfo.json',
        project = {
            name = 'Nominatim',
            description = 'OSM search engine.',
            project_url = 'https://nominatim.openstreetmap.org',
            doc_url = 'https://nominatim.org/release-docs/develop/',
            contact_name = 'Sarah Hoffmann',
            contact_email = 'lonvia@denofr.de'
        }
    }
    format.tags = tags

    set_keyorder(format, {'data_format', 'data_url', 'project', 'tags'})
    set_keyorder(format.project, {'name', 'description', 'project_url', 'doc_url',
                    'contact_name', 'contact_email'})

    print(json.encode(format))
end

print_taginfo()
