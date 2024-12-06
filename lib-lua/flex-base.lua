-- This is just an alias for the Nominatim themepark theme module
local flex = require('themes/nominatim/init')

function flex.load_topic(name, cfg)
    local topic_file = debug.getinfo(1, "S").source:sub(2):match("(.*/)") .. 'themes/nominatim/topics/'.. name .. '.lua'

    if topic_file == nil then
        error('Cannot find topic: ' .. name)
    end

    loadfile(topic_file)(nil, flex, cfg or {})
end

return flex
