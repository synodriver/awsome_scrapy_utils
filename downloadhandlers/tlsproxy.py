# -*- coding: utf-8 -*-
import base64
from typing import Optional

import aiohttp
from scrapy import signals
from scrapy.core.downloader.handlers.http11 import HTTP11DownloadHandler as HTTPDownloadHandler
from scrapy.crawler import Crawler
from scrapy.http import Headers, Request, Response
from scrapy.responsetypes import responsetypes
from scrapy.settings import Settings
from scrapy.spiders import Spider
from scrapy.utils.defer import deferred_f_from_coro_f, deferred_from_coro
from twisted.internet.defer import Deferred

# ssl._create_default_https_context = ssl._create_unverified_context


class TLSProxyDownloadHandler(HTTPDownloadHandler):
    def __init__(self, crawler: Optional[Crawler] = None):
        super().__init__(crawler)
        self.client = None  # type: aiohttp.ClientSession
        crawler.signals.connect(self.engine_started, signals.engine_started)

    async def engine_started(self, signal, sender):
        client = aiohttp.ClientSession()
        self.client = await client.__aenter__()

    async def download_request(self, request: Request) -> Response:
        """
        启动此handler方法是request.meta['tls'] = {"someextraconfig": xxx}
        """
        if "tls" in request.meta:
            return await self._download_request(request)
        return await super().download_request(request)  # 普通下载

    async def _download_request(self, request: Request) -> Response:
        """转发给tlsproxy下载逻辑"""
        post_data = {
            "method": request.method,
            "url": request.url,
            "timeout": request.meta.get(
                "download_timeout", self.crawler.settings.get("DOWNLOAD_TIMEOUT")
            ),
            "headers": request.headers.to_unicode_dict(),
        }
        if request.body:
            post_data["body"] = base64.b64encode(request.body).decode()
        if "proxy" in request.meta:
            post_data["proxy"] = request.meta["proxy"]
        if "header_order" in request.meta["tls"]:
            post_data["header_order"] = request.meta["tls"]["header_order"]
        if "pheader_order" in request.meta["tls"]:
            post_data["pheader_order"] = request.meta["tls"]["pheader_order"]
        if request.meta.get(
            "dont_redirect", False
        ):  # and not spider.settings.get("REDIRECT_ENABLED", True):
            post_data["allow_redirects"] = False
        if "dont_redirect" not in request.meta and not self.crawler.settings.get(
            "REDIRECT_ENABLED", True
        ):
            post_data["allow_redirects"] = False
        if "verify" in request.meta["tls"]:
            post_data["verify"] = request.meta["tls"]["verify"]
        if "cert" in request.meta["tls"]:
            post_data["cert"] = request.meta["tls"]["cert"]
        if "ja3" in request.meta["tls"]:
            post_data["ja3"] = request.meta["tls"]["ja3"]
        if "force_http1" in request.meta["tls"]:
            post_data["force_http1"] = request.meta["tls"]["force_http1"]
        if "supported_signature_algorithms" in request.meta["tls"]:
            post_data["supported_signature_algorithms"] = request.meta["tls"][
                "supported_signature_algorithms"
            ]
        if "cert_compression_algo" in request.meta["tls"]:
            post_data["cert_compression_algo"] = request.meta["tls"][
                "cert_compression_algo"
            ]
        if "record_size_limit" in request.meta["tls"]:
            post_data["record_size_limit"] = request.meta["tls"]["record_size_limit"]
        if "delegated_credentials" in request.meta["tls"]:
            post_data["delegated_credentials"] = request.meta["tls"][
                "delegated_credentials"
            ]
        if "supported_versions" in request.meta["tls"]:
            post_data["supported_versions"] = request.meta["tls"]["supported_versions"]
        if "pskkey_exchange_modes" in request.meta["tls"]:
            post_data["pskkey_exchange_modes"] = request.meta["tls"][
                "pskkey_exchange_modes"
            ]
        if "signature_algorithms_cert" in request.meta["tls"]:
            post_data["signature_algorithms_cert"] = request.meta["tls"][
                "signature_algorithms_cert"
            ]
        if "key_share_curves" in request.meta["tls"]:
            post_data["key_share_curves"] = request.meta["tls"]["key_share_curves"]
        if "h2settings" in request.meta["tls"]:
            post_data["h2settings"] = request.meta["tls"]["h2settings"]
        if "h2settings_order" in request.meta["tls"]:
            post_data["h2settings_order"] = request.meta["tls"]["h2settings_order"]
        if "h2connectionflow" in request.meta["tls"]:
            post_data["h2connectionflow"] = request.meta["tls"]["h2connectionflow"]
        if "h2headerpriority" in request.meta["tls"]:
            post_data["h2headerpriority"] = request.meta["tls"]["h2headerpriority"]
        if "h2priorityframes" in request.meta["tls"]:
            post_data["h2priorityframes"] = request.meta["tls"]["h2priorityframes"]

        async with self.client.post(
            self.crawler.settings.get("TLSPROXY", "http://127.0.0.1:11000/request"),
            json=post_data,
        ) as response:
            # headers = Headers(response.headers)
            respjson = await response.json()
            status = respjson["status"]
            headers = Headers(respjson["headers"])
            del headers["content-encoding"]  # 防止scrapy二次解压
            body = base64.b64decode(respjson["body"])
            respcls = responsetypes.from_args(
                headers=headers, url=str(response.url), body=body
            )
            return respcls(
                url=str(response.url),
                status=status,
                headers=headers,
                body=body,
                flags=["tls"],
                request=request
                # protocol=response.version,
            )

    async def close(self):
        await self.client.__aexit__(None, None, None)
        await super().close()
