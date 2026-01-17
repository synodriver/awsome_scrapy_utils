import asyncio
from functools import partial
from typing import Optional

from requests import Session
from requests_curl import CURLAdapter
from scrapy import signals
from scrapy.core.downloader.handlers.http11 import (
    HTTP11DownloadHandler as HTTPDownloadHandler,
)
from scrapy.crawler import Crawler
from scrapy.http import Headers, Request, Response
from scrapy.responsetypes import responsetypes
from scrapy.settings import Settings
from scrapy.spiders import Spider
from scrapy.utils.defer import deferred_from_coro
from twisted.internet.defer import Deferred


class CurlDownloadHandler(HTTPDownloadHandler):
    def __init__(self, crawler: Optional[Crawler] = None):
        super().__init__(crawler)
        self.client = None  # type: Session
        crawler.signals.connect(self.engine_started, signals.engine_started)

    def engine_started(self, signal, sender):
        client = Session()
        client.mount("https://", CURLAdapter())
        client.headers = {}
        self.client = client.__enter__()

    async def download_request(self, request: Request) -> Response:
        if request.meta.get("tls"):
            return await self._download_request(request)
        return await super().download_request(request)  # 普通下载

    async def _download_request(self, request: Request) -> Response:
        """pycurl下载逻辑"""
        # asyncio.get_running_loop().run_in_executor(None, self.client.request, request.method)
        pfunc = partial(
            self.client.request,
            request.method,
            request.url,
            data=request.body,
            headers=request.headers.to_unicode_dict(),
            cookies=request.cookies,
        )
        response = await asyncio.get_running_loop().run_in_executor(None, pfunc)
        del response.headers["content-encoding"]  # 防止scrapy二次解压
        headers = Headers(response.headers)
        respcls = responsetypes.from_args(
            headers=headers, url=response.url, body=response.content
        )
        return respcls(
            url=response.url,
            status=response.status_code,
            headers=headers,
            body=response.content,
            flags=["antitls"],
            request=request,
        )  # scrapy 2.6

    async def close(self):
        self.client.__exit__()
        await super().close()
