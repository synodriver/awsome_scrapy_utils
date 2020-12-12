# -*- coding: utf-8 -*-
import logging

from scrapy import signals
from scrapy.responsetypes import responsetypes
import scrapy
import httpx

logger = logging.getLogger(__name__)


class HttpxMiddleware:
    """
    可以下载http2 处理socks代理
    """

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def spider_opened(self, spider):
        spider.logger.info('Spider  %s opened middleware: %s' % (spider.name, self.__class__.__name__))

    async def process_request(self, request: scrapy.Request, spider):
        logger.info("进来的meta是 {0}".format(request.meta))
        if request.meta.get("use_httpx", False):
            async with httpx.AsyncClient() as client:
                req = client.build_request(request.method, request.url)
                resp = await client.send(req)
                body = resp.read()
                resp_cls: type = responsetypes.from_args(headers=resp.headers, url=resp.url, body=resp.text)
                response = resp_cls(
                    url=resp.url,
                    status=resp.status_code,
                    headers=resp.headers,
                    body=body,
                )
                return response

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):
        pass
