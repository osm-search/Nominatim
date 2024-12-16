-- This is just an alias for the Nominatim themepark full topic
local flex = require('flex-base')

flex.load_topic('full', {with_extratags = true})

return flex
