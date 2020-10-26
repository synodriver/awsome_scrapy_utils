# -*- coding: utf-8 -*-
import logging
import asyncio

from aioaria2 import Aria2WebsocketTrigger
from aiohttp.client_exceptions import ContentTypeError
from twisted.internet.defer import Deferred
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

    def __init__(self, id_: str, url: str, token: str, url_field: str,
                 option_field: str):
        self.id = id_
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

    def open_spider(self, spider):
        loop = asyncio.get_event_loop()
        return Deferred.fromFuture(loop.create_task(self._open_spider(spider)))

    async def _open_spider(self, spider):
        self.client = await Aria2WebsocketTrigger.new(self.id, self.url, token=self.token)
        if hasattr(self, "onResult"):
            self.client.onResult(self.onResult)
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

    async def _close_spider(self, spider):
        await self.client.close()
        spider.logger.debug("关闭Aria2Pipeline")

    def close_spider(self, spider):
        # It would be great convenience if this method can be defined with async def.
        # However,such behavior would cause "never awaited" warning.
        # see https://docs.scrapy.org/en/latest/topics/coroutines.html#coroutine-support
        loop = asyncio.get_event_loop()
        return Deferred.fromFuture(loop.create_task(self._close_spider(spider)))

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
            pass
            raise e
        return item
