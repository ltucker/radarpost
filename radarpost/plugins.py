"""
a very loosey-goosey plug-in system
"""

import logging

__all__ = ['get', 'register', 'plugin']

log = logging.getLogger(__name__)

ENTRY_POINT = 'radarpost_plugins'
_plugins = None

def get(slot):
    global _plugins
    if _plugins is None:
        _plugins = {}
        _search()

    return _plugins.setdefault(slot, [])
    return _plugins[slot]

def register(thing, slot):
    """
    declare a plugin
    """
    get(slot).append(thing)

def plugin(slot):
    """
    decorator to declare a plugin
    """
    def dd(thing):
        register(thing, slot)
        return thing
    return dd

def _search():
    from pkg_resources import working_set as ws
    log.debug("Searching for plugins...")
    for entry in ws.iter_entry_points(ENTRY_POINT):
        log.debug('Loading plugin %s from %s', entry.name, entry.dist.location)

        try:
            entry.load(require=True)
        except:
            import traceback
            traceback.print_exc()
            log.error("Error loading plugin %s from %s: %s" % (entry.name, entry.dist.location, traceback.format_exc()))
