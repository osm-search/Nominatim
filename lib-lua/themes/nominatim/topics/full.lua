local _, flex, cfg = ...

local group
if cfg.with_extratags then
    group = 'extra'
else
    group = 'delete'
end

flex.set_main_tags('all_boundaries')
flex.modify_main_tags('natural')
flex.modify_main_tags('street/' .. (cfg.street_theme or 'default'))
flex.modify_main_tags('poi/' .. group)

flex.set_name_tags('core')
flex.modify_name_tags('address')
flex.modify_name_tags('poi')

flex.set_address_tags('core')
flex.modify_address_tags('houses')

flex.ignore_keys('metatags')
flex.add_for_extratags('required')

if cfg.with_extratags then
    flex.set_unused_handling{delete_keys = {'tiger:*'}}
    flex.add_for_extratags('name')
    flex.add_for_extratags('address')
else
    flex.ignore_keys('name')
    flex.ignore_keys('address')
end
