-- Prints taginfo project description in the standard output
--

-- create fake "osm2pgsql" table for flex-base, originally created by the main C++ program
osm2pgsql = {}
function osm2pgsql.define_table(...) end

-- provide path to flex-style lua file
flex = require('import-extratags')
local json = require ('dkjson')


------------ helper functions ---------------------

function get_key_description(key, description)
    local desc = {}
    desc.key = key
    desc.description = description
    set_keyorder(desc, {'key', 'description'})
    return desc
end

-- Sets the key order for the resulting JSON table
function set_keyorder(table, order)
    setmetatable(table, {
        __jsonorder = order
    })
end


-- Prints the collected tags in the required format in JSON
function print_taginfo()
    local tags = {}

    for _, k in ipairs(flex.TAGINFO_MAIN.keys) do
        local desc = get_key_description(k, 'POI/feature in the search database')
        if flex.TAGINFO_MAIN.delete_tags[k] ~= nil then
            desc.description = string.format('%s(except for values: %s).', desc.description,
                                table.concat(flex.TAGINFO_MAIN.delete_tags[k], ', '))
        end
        table.insert(tags, desc)
    end

    for k, _ in pairs(flex.TAGINFO_NAME_KEYS) do
        local desc = get_key_description(k, 'Searchable name of the place.')
        table.insert(tags, desc)
    end
    for k, _ in pairs(flex.TAGINFO_ADDRESS_KEYS) do
        local desc = get_key_description(k, 'Used to determine the address of a place.')
        table.insert(tags, desc)
    end

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
