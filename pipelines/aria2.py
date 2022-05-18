# -*- coding: utf-8 -*-
import logging

from aioaria2 import Aria2WebsocketTrigger
from aiohttp.client_exceptions import ContentTypeError
from scrapy.utils.defer import deferred_f_from_coro_f
from itemadapter import ItemAdapter

logger = logging.getLogger(__name__)


# TODO 修改为websocket通信
class Aria2Pipeline:
    """
    可以提交aria2下载的pipeline,比内置的FilePipeline更快
    需要如下设置
    ARIA2_ID
    ARIA2_URL aria2地址
    ARIA2_TOKEN  默认None
    ARIA2_URLS_FIELD 包含url的字段 默认file_urls
    ARIA2_OPTION_FIELD  包含option的字段 默认options
    """

    def __init__(self, url: str, token: str, url_field: str,
                 option_field: str):
        self.url = url
        self.token = token
        self.url_field = url_field
        self.option_field = option_field
        self.client: Aria2WebsocketTrigger = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.get("ARIA2_ID"), crawler.settings.get("ARIA2_URL"),
                   crawler.settings.get("ARIA2_TOKEN"),
                   crawler.settings.get("ARIA2_URLS_FIELD", "file_urls"),
                   crawler.settings.get("ARIA2_OPTION_FIELD", "options"))

    @deferred_f_from_coro_f
    async def open_spider(self, spider):
        self.client = await Aria2WebsocketTrigger.new(self.url, token=self.token)
        if hasattr(self, "onDownloadStart"):
            self.client.onDownloadStart(self.onDownloadStart)
        if hasattr(self, "onDownloadPause"):
            self.client.onDownloadPause(self.onDownloadPause)
        if hasattr(self, "onDownloadStop"):
            self.client.onDownloadStop(self.onDownloadStop)
        if hasattr(self, "onDownloadComplete"):
            self.client.onDownloadComplete(self.onDownloadComplete)
        if hasattr(self, "onDownloadError"):
            self.client.onDownloadError(self.onDownloadError)
        if hasattr(self, "onBtDownloadComplete"):
            self.client.onBtDownloadComplete(self.onBtDownloadComplete)

        spider.logger.debug("打开Aria2Pipeline")

    @deferred_f_from_coro_f
    async def close_spider(self, spider):
        # It would be great convenience if this method can be defined with async def.
        # However,such behavior would cause "never awaited" warning.
        # see https://docs.scrapy.org/en/latest/topics/coroutines.html#coroutine-support
        await self.client.close()
        spider.logger.debug("关闭Aria2Pipeline")

    async def process_item(self, item, spider):
        ad = ItemAdapter(item)
        download_url: list = ad[self.url_field]
        if not isinstance(download_url, list):
            download_url = [download_url]
        options = ad[self.option_field]
        try:
            data = await self.client.addUri(download_url, options)
            logger.debug("downloading {0},aria2 gid {1}".format(download_url, data))
        except ContentTypeError as e:
            raise e
        return item
