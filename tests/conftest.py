import asyncio
import inspect


def pytest_pyfunc_call(pyfuncitem):
    if inspect.iscoroutinefunction(pyfuncitem.obj):
        asyncio.run(pyfuncitem.obj(**pyfuncitem.funcargs))
        return True
    return None
