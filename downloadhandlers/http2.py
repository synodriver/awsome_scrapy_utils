# -*- coding: utf-8 -*-
from typing import Optional

import httpx
from scrapy import signals
from scrapy.core.downloader.handlers.http11 import (
    HTTP11DownloadHandler as HTTPDownloadHandler,
)
from scrapy.crawler import Crawler
from scrapy.http import Headers, Request, Response
from scrapy.responsetypes import responsetypes
from scrapy.settings import Settings
from scrapy.spiders import Spider
from scrapy.utils.defer import deferred_f_from_coro_f, deferred_from_coro
from twisted.internet.defer import Deferred


class HttpxDownloadHandler(HTTPDownloadHandler):
    def __init__(self, crawler: Optional[Crawler] = None):
        super().__init__(crawler)
        self.client = None
        crawler.signals.connect(self.engine_started, signals.engine_started)

    async def engine_started(self, signal, sender):
        client = httpx.AsyncClient(http2=True)
        self.client = await client.__aenter__()

    async def download_request(self, request: Request) -> Response:
        if request.meta.get("h2"):
            return await self._download_request(request)
        return await super().download_request(request)  # 普通下载

    async def _download_request(self, request: Request) -> Response:
        """httpx下载逻辑"""
        response = await self.client.request(
            request.method,
            request.url,
            content=request.body,
            headers=request.headers.to_unicode_dict(),
            cookies=request.cookies,
        )
        del response.headers["content-encoding"]  # 防止scrapy二次解压
        headers = Headers(response.headers)
        respcls = responsetypes.from_args(
            headers=headers, url=response.url, body=response.content
        )
        return respcls(
            url=str(response.url),
            status=response.status_code,
            headers=headers,
            body=response.content,
            flags=["httpx"],
            request=request,
            protocol=response.http_version,
        )

    async def close(self):
        await self.client.__aexit__()
        await super().close()
