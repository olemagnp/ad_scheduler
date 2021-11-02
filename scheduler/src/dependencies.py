import aiohttp
import os

ha_session = aiohttp.ClientSession("http://supervisor/core/api", headers={"Authorization": f"Bearer {os.environ['SUPERVISOR_TOKEN']}"})

def make_url(*parts):
    return os.path.join(parts)