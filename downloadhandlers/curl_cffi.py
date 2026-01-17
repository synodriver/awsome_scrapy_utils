import random
from typing import Optional
from urllib.parse import urldefrag

try:
    import cycurl
    from cycurl import CurlError
    from cycurl.requests import AsyncSession

    OPERATION_TIMEDOUT = cycurl.CURLE_OPERATION_TIMEDOUT
except ImportError:
    from curl_cffi import CurlError
    from curl_cffi.const import CurlECode
    from curl_cffi.requests import AsyncSession

    OPERATION_TIMEDOUT = CurlECode.OPERATION_TIMEDOUT
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


class CurlCFFIDownloadHandler(HTTPDownloadHandler):
    def __init__(self, crawler: Optional[Crawler] = None):
        super().__init__(crawler)
        self.session = AsyncSession()
        crawler.signals.connect(self.engine_started, signals.engine_started)

    async def engine_started(self, *args, **kwargs):
        # print(f"{self.__class__.__name__} aenter, {args}, {kwargs}")  # todo del
        await self.session.__aenter__()

    async def download_request(self, request: Request) -> Response:
        # print(f"{self.__class__.__name__} download_request {request.url}{request.meta}")
        if request.meta.get("tls"):
            # print(f"{request.url} have tls")
            return await self._download_request(request)
        return await super().download_request(request)  # 普通下载

    async def _download_request(self, request: Request) -> Response:
        """curl-cffi下载逻辑"""
        # spider = self.crawler.spider
        # asyncio.get_running_loop().run_in_executor(None, self.client.request, request.method)
        impersonate = request.meta.get("impersonate") or random.choice(
            ["chrome99", "chrome101", "chrome110", "edge99", "edge101", "chrome107"]
        )
        timeout = request.meta.get(
            "download_timeout", self.crawler.settings.get("DOWNLOAD_TIMEOUT")
        )
        proxy = request.meta.get("proxy")
        try:
            response = await self.session.request(
                request.method,
                request.url,
                data=request.body,
                headers=request.headers.to_unicode_dict(),
                proxies=(
                    {
                        "http": proxy,
                        "https": proxy,
                    }
                    if proxy
                    else None
                ),
                timeout=timeout,
                impersonate=impersonate,
            )
        except CurlError as e:
            if e.code == OPERATION_TIMEDOUT:
                url = urldefrag(request.url)[0]
                raise TimeoutError(
                    f"Requesting {url} took longer than {timeout} seconds."
                ) from e
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
            protocol=response.http_version,
        )  # scrapy 2.6

    async def close(self):
        # print(f"{self.__class__.__name__} aexit")  # todo del
        await self.session.__aexit__()
        await super(CurlCFFIDownloadHandler, self).close()
