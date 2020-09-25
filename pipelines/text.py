# -*- coding: utf-8 -*-
import logging
import asyncio
from typing import List
import aiofiles
import scrapy
from twisted.internet.defer import Deferred
from itemadapter import ItemAdapter

logger = logging.getLogger(__name__)


class TextPipeline:
    """
    写入txt文件
    需要在settings.py中指定
    TEXT_PATH  要保存的文件的地址
    TEXT_FIELDS item中需要保存的字段 可以有多个 但数量必须和TEXT_FORMAT中的匹配 e.g. TEXT_FIELDS=["ha","wa","yi"]
    TEXT_FORMAT 文件格式  str 型如  '{0},{1},{2}'字符串
    """

    def __init__(self, path: str, text_fields: List[str], text_format: str):
        """
        "../data/download_url.txt"
        :param path: 文件路径
        """
        self.path = path
        self.text_fields = text_fields
        self.text_format = text_format
        self.file = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.get("TEXT_PATH"), crawler.settings.getlist("TEXT_FIELDS"),
                   crawler.settings.get("TEXT_FORMAT"))

    async def _open_spider(self, spider: scrapy.Spider):
        self.file = await aiofiles.open(self.path, "a+", encoding="utf-8")
        spider.logger.debug("打开TextPipeline")

    def open_spider(self, spider):
        loop = asyncio.get_event_loop()
        return Deferred.fromFuture(loop.create_task(self._open_spider(spider)))

    async def _close_spider(self, spider):
        await self.file.flush()
        await self.file.close()
        spider.logger.debug("关闭TextPipeline")

    def close_spider(self, spider):
        loop = asyncio.get_event_loop()
        return Deferred.fromFuture(loop.create_task(self._close_spider(spider)))

    async def process_item(self, item, spider):
        ad = ItemAdapter(item)
        # download_url = ad[self.text_field]
        formatter: List[str] = [ad[text_field] for text_field in self.text_fields]
        text = self.text_format.format(*formatter)
        logger.debug("写入文件 {0}".format(text))
        await self.file.write(text + "\n")
        await self.file.flush()
        return item
