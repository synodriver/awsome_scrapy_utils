# -*- coding: utf-8 -*-
import logging

from databases import Database
from itemadapter import ItemAdapter
from scrapy.utils.defer import deferred_f_from_coro_f

logger = logging.getLogger(__name__)


class SqlPipeline:
    """
    异步插入mysql postgre 或者sqlite
    settings.py 中需要添加设置
    SQL_URL
    """

    def __init__(self, url):
        self.url = url  # 数据库url
        self.pool: Database = Database(url)

    @classmethod
    def from_crawler(cls, crawler):
        self = cls(crawler.settings.get("SQL_URL"))
        return self

    @deferred_f_from_coro_f
    async def open_spider(self, spider):
        """
        等下这个要进行twisted套娃
        :param spider:
        :return:
        """
        await self.pool.connect()
        spider.logger.debug("打开MysqlPipeline 并建立连接")

    @deferred_f_from_coro_f
    async def close_spider(self, spider):
        await self.pool.disconnect()
        spider.logger.debug("关闭MysqlPipeline")

    async def process_item(self, item, spider):
        """
        具体的插入操作，可能需要自己重写
        :param item:
        :param spider:
        :return:
        """
        ad = ItemAdapter(item)
        download_url = ad["download_url"]
        file_name = ad["name"]
        refer = ad["refer"]
        sql = "insert into test.urls (download_url,file_name,refer) values (:download_url,:file_name,:refer)"
        logger.debug("执行sql {0}".format(sql))
        await self.pool.execute(
            sql, {"download_url": download_url, "file_name": file_name, "refer": refer}
        )
        return item


import logging

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Session, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

logging.getLogger("aiosqlite").setLevel(logging.INFO)


class SQLModulePipeline:
    def __init__(self, url: str, echo: bool = False):
        """
        :param url: DB's url
        """
        self.url = url
        self.echo = echo
        self.engine = None

    @classmethod
    def from_crawler(cls, crawler: Crawler):
        return cls(
            crawler.settings.get("SQL_URL"), crawler.settings.getbool("SQL_ECHO")
        )

    def open_spider(self, spider: scrapy.Spider):
        spider.logger.debug("打开sqlmodel")
        self.engine = create_async_engine(self.url, echo=self.echo)

    async def process_item(self, item, spider):
        async with AsyncSession(self.engine) as session:
            session.add(item)
            await session.commit()

    def close_spider(self, spider):
        self.engine = None
        spider.logger.debug("关闭sqlmodel")
