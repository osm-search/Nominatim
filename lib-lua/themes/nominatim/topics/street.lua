local _, flex, cfg = ...

flex.set_main_tags('admin')
flex.modify_main_tags('street/' .. (cfg.street_theme or 'default'))
flex.modify_main_tags{boundary = {postal_code = 'always'}}

flex.set_name_tags('core')

flex.set_address_tags('core')
flex.set_postcode_fallback(false)

flex.ignore_keys('metatags')

if cfg.with_extratags then
    flex.set_unused_handling{delete_keys = {'tiger:*'}}
    flex.add_for_extratags('name')
    flex.add_for_extratags('address')
else
    flex.ignore_keys('name')
    flex.ignore_keys('address')
end
