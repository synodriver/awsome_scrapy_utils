# -*- coding: utf-8 -*-
"""
Copyright (c) 2008-2024 synodriver <diguohuangjiajinweijun@gmail.com>
"""
import ctypes

lib = ctypes.cdll.LoadLibrary("libcomandy.so")
_request = lib.request
_request.argtypes = [ctypes.c_char_p]
_request.restype = ctypes.c_char_p

_add_dns = lib.add_dns
_add_dns.argtypes = [ctypes.c_char_p, ctypes.c_int]
_add_dns.restype = ctypes.c_char_p

import asyncio
import json
from functools import partial


async def request(method: str, url: str, headers: dict = None, data: str = None):
    payload = {"method": method, "url": url, "headers": headers or {}}
    if data is not None:
        payload["data"] = data
    payload = json.dumps(payload).encode("utf-8")
    ret = await asyncio.get_running_loop().run_in_executor(
        None, partial(_request, payload)
    )
    try:
        return json.loads(ret.decode("utf8"))
    finally:
        ctypes.windll.msvcrt.free(ret)
