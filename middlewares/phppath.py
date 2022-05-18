# -*- coding: utf-8 -*-
"""
在一些php网站里面，经常出现诸如:path之类的header
"""
from urllib import parse
import logging

import scrapy
from scrapy import signals

logger = logging.getLogger(__name__)


class PHPPathMiddleware:
    """
    给请求增加:path的header
    """
    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request: scrapy.Request, spider):
        request.headers[
            ":path"
        ] = f"{parse.urlsplit(request.url).path}?{parse.urlsplit(request.url).query}"

        logger.debug("修改了headers的:path 为{0}".format(request.headers[":path"]))

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):
        pass

    def spider_opened(self, spider):
        spider.logger.info(
            f'Spider  {spider.name} opened middleware: {self.__class__.__name__}'
        )
