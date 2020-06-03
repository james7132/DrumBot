import pkgutil
import sys
import logging
from aiohttp import web
from hourai.utils import uvloop
from hourai.db.storage import Storage


log = logging.getLogger(__name__)
run_app = web.run_app


async def create_app(config) -> web.Application:
    uvloop.try_install()

    storage = Storage(config)
    await storage.init()

    module = sys.modules[__name__]
    app = web.Application()
    app["storage"] = storage
    for importer, name, ispkg in pkgutil.iter_modules(module.__path__):
        if not ispkg:
            continue
        module = importer.find_module(name).load_module(name)
        app.add_subapp(f'/api/{module.__name__}/',
                       module.create_app(config, storage))

    for route in app.router.routes():
        log.info(f'Route: {route}')
    log.info('App initialized.')
    return app
