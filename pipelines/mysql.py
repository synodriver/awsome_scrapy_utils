# -*- coding: utf-8 -*-
import logging
import asyncio

import aiomysql
from twisted.internet.defer import Deferred
from itemadapter import ItemAdapter

logger = logging.getLogger(__name__)


class MysqlPipeline:
    """
    异步插入mysql
    settings.py 中需要添加设置
    MYSQL_HOST
    MYSQL_PORT
    MYSQL_USER
    MYSQL_PASSWORD
    MYSQL_DB
    MYSQL_TABLE
    """

    def __init__(self, host, port, user, password, db, table):
        self.host: str = host
        self.port: int = port
        self.user: str = user
        self.password: str = password
        self.db: str = db
        self.table: str = table
        self.pool: aiomysql.Pool = None

    @classmethod
    def from_crawler(cls, crawler):
        self = cls(crawler.settings.get("MYSQL_HOST"), crawler.settings.getint("MYSQL_PORT"),
                   crawler.settings.get("MYSQL_USER"), crawler.settings.get("MYSQL_PASSWORD"),
                   crawler.settings.get("MYSQL_DB"), crawler.settings.get("MYSQL_TABLE"))
        return self

    async def _open_spider(self, spider):
        """
        等下这个要进行twisted套娃
        :param spider:
        :return:
        """
        self.pool = await aiomysql.create_pool(host=self.host, port=self.port, user=self.user,
                                               password=self.password, db=self.db, charset="utf8", autocommit=True)
        spider.logger.debug("打开MysqlPipeline 并建立连接")

    def open_spider(self, spider):
        """
        用twisted包装
        :param spider:
        :return:
        """
        loop = asyncio.get_event_loop()
        return Deferred.fromFuture(loop.create_task(self._open_spider(spider)))

    def close_spider(self, spider):
        self.pool.close()
        spider.logger.debug("关闭MysqlPipeline")

    async def process_item(self, item, spider):
        """
        具体的插入操作，可能需要自己重写
        :param item:
        :param spider:
        :return:
        """
        ad = ItemAdapter(item)
        download_url = format_sql(ad["download_url"])
        file_name = format_sql(ad["name"])
        refer = format_sql(ad["refer"])
        sql = "insert into %s (download_url,file_name,refer) values (%s,%s,%s)"
        logger.debug("执行sql {0}".format(sql))
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, (self.table, download_url, file_name, refer))
                await conn.commit()
        return item
