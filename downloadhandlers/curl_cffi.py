import random
from typing import Optional
from urllib.parse import urldefrag

from curl_cffi import const, curl
from curl_cffi.requests import AsyncSession
from scrapy import signals
from scrapy.core.downloader.handlers.http import HTTPDownloadHandler
from scrapy.crawler import Crawler
from scrapy.http import Headers, Request, Response
from scrapy.responsetypes import responsetypes
from scrapy.settings import Settings
from scrapy.spiders import Spider
from scrapy.utils.defer import deferred_f_from_coro_f, deferred_from_coro
from twisted.internet.defer import Deferred


class CurlCFFIDownloadHandler(HTTPDownloadHandler):
    def __init__(self, settings: Settings, crawler: Optional[Crawler] = None):
        super().__init__(settings, crawler)
        self.session = AsyncSession()
        crawler.signals.connect(self._engine_started, signals.engine_started)

    @deferred_f_from_coro_f
    async def _engine_started(self, signal, sender):
        # print(f"{self.__class__.__name__} aenter")  # todo del
        await self.session.__aenter__()

    def download_request(self, request: Request, spider: Spider) -> Deferred:
        if request.meta.get("tls"):
            return deferred_from_coro(self._download_request(request, spider))
        return super().download_request(request, spider)  # 普通下载

    async def _download_request(self, request: Request, spider: Spider) -> Response:
        """curl-cffi下载逻辑"""
        # asyncio.get_running_loop().run_in_executor(None, self.client.request, request.method)
        impersonate = request.meta.get("impersonate") or random.choice(
            ["chrome99", "chrome101", "chrome110", "edge99", "edge101", "chrome107"]
        )
        timeout = request.meta.get(
            "download_timeout", spider.settings.get("DOWNLOAD_TIMEOUT")
        )
        proxy = request.meta.get("proxy")
        try:
            response = await self.session.request(
                request.method,
                request.url,
                data=request.body,
                headers=request.headers.to_unicode_dict(),
                proxies={
                    "http": proxy,
                    "https": proxy,
                }
                if proxy
                else None,
                timeout=timeout,
                impersonate=impersonate,
            )
        except curl.CurlError as e:
            if e.code == const.CurlECode.OPERATION_TIMEDOUT:
                url = urldefrag(request.url)[0]
                raise TimeoutError(
                    f"Requesting {url} took longer than {timeout} seconds."
                ) from e


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
            protocol=response.http_version,
        )  # scrapy 2.6

    @deferred_f_from_coro_f
    async def close(self):
        # print(f"{self.__class__.__name__} aexit")  # todo del
        await self.session.__aexit__()
        super(CurlCFFIDownloadHandler, self).close()
