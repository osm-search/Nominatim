-- This is just an alias for the Nominatim themepark theme module
local flex = require('themes/nominatim/init')

function flex.load_topic(name, cfg)
    local topic_file = debug.getinfo(1, "S").source:sub(2):match("(.*/)") .. 'themes/nominatim/topics/'.. name .. '.lua'

    loadfile(topic_file)(nil, flex, cfg or {})
end

return flex
