# -*- coding: utf-8 -*-
import logging
from scrapy import signals
import scrapy
import aiohttp

logger = logging.getLogger(__name__)


class AiohttpMiddleware:
    """
    scrapy timeout就用aiohttp试试
    用于解决一些蜜汁bug
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
        if request.meta.get("use_aiohttp", False):
            logger.debug("使用aiohttp进行尝试")
            url = request.url
            headers = dict(request.headers.to_unicode_dict())
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    html: bytes = await resp.read()
                    return scrapy.http.HtmlResponse(url=request.url, status=resp.status, headers=request.headers,
                                                    body=html, request=request, encoding=resp.get_encoding())

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):

        pass
