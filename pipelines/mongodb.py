# -*- coding: utf-8 -*-
import logging

import scrapy
from itemadapter import ItemAdapter
from motor import motor_asyncio
from pymongo import MongoClient
from twisted.internet.threads import deferToThread

logger = logging.getLogger(__name__)


class DeferredMongoDBPipeline:
    """
    异步插入mongodb
    settings.py 中需要添加设置
    MONGODB_HOST
    MONGODB_PORT
    MONGODB_USER
    MONGODB_PASSWORD
    MONGODB_DB
    """

    def __init__(self, host, port, user, password, db):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db
        self.client: MongoClient = None

    @classmethod
    def from_crawler(cls, crawler):
        self = cls(
            crawler.settings.get("MONGODB_HOST"),
            crawler.settings.getint("MONGODB_PORT"),
            crawler.settings.get("MONGODB_USER"),
            crawler.settings.get("MONGODB_PASSWORD"),
            crawler.settings.get("MONGODB_DB"),
        )
        return self

    def open_spider(self, spider):
        self.client = MongoClient(
            "mongodb://{user}:{password}@{host}:{port}".format(
                user=self.user, password=self.password, host=self.host, port=self.port
            )
        )

    def close_spider(self, spider):
        self.client.close()

    def _process_item(self, item, spider):
        collection = self.client[self.db]["test"]  # 改成你自己的集合名字
        obj: dict = ItemAdapter(item).asdict()
        collection.insert_one(obj)
        logger.debug("执行mongodb的insert_one:{0}".format(obj))

    def process_item(self, item, spider):
        return deferToThread(self._process_item, item, spider)


class AsyncMongoDBPipeline:
    """
    异步插入mongodb
    settings.py 中需要添加设置
    MONGODB_HOST
    MONGODB_PORT
    MONGODB_USER
    MONGODB_PASSWORD
    MONGODB_DB
    """

    def __init__(self, host, port, user, password, db):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db
        self.client: motor_asyncio.AsyncIOMotorClient = None

    @classmethod
    def from_crawler(cls, crawler):
        self = cls(
            crawler.settings.get("MONGODB_HOST"),
            crawler.settings.getint("MONGODB_PORT"),
            crawler.settings.get("MONGODB_USER"),
            crawler.settings.get("MONGODB_PASSWORD"),
            crawler.settings.get("MONGODB_DB"),
        )
        return self

    def open_spider(self, spider):
        self.client = motor_asyncio.AsyncIOMotorClient(
            "mongodb://{user}:{password}@{host}:{port}".format(
                user=self.user, password=self.password, host=self.host, port=self.port
            )
        )

    def close_spider(self, spider):
        self.client.close()

    async def process_item(self, item: scrapy.Item, spider: scrapy.Spider):
        collection = self.client[self.db]["test"]  # 改成你自己的集合名字
        obj: dict = ItemAdapter(item).asdict()
        await collection.insert_one(obj)
        logger.debug("执行mongodb的insert_one:{0}".format(obj))


if __name__ == "__main__":
    pass
