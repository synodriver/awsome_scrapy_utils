# -*- coding: utf-8 -*-
import logging

import scrapy.downloadermiddlewares.retry as retry
from scrapy import signals

logger = logging.getLogger(__name__)


class LoggedRetryMiddleware(retry.RetryMiddleware):
    """
    失败后会记录日志的重试中间件
    需要在settings.py 中加入 FAILED_URL_PATH
    """

    def __init__(self, settings):
        super().__init__(settings)
        self.log_path = settings.get("FAILED_URL_PATH")

    @classmethod
    def from_crawler(cls, crawler):
        s = cls(crawler.settings)
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def spider_opened(self, spider):
        spider.logger.info(
            "Spider  %s opened middleware: %s" % (spider.name, self.__class__.__name__)
        )

    def _retry(self, request, reason, spider):
        retries = request.meta.get("retry_times", 0) + 1

        retry_times = self.max_retry_times

        if "max_retry_times" in request.meta:
            retry_times = request.meta["max_retry_times"]

        stats = spider.crawler.stats
        if retries <= retry_times:
            logger.debug(
                "Retrying %(request)s (failed %(retries)d times): %(reason)s",
                {"request": request, "retries": retries, "reason": reason},
                extra={"spider": spider},
            )
            retryreq = request.copy()
            retryreq.meta["retry_times"] = retries
            # retryreq.meta["use_aiohttp"] = True
            # logger.debug("给meta添加字段{0}".format(retryreq.meta))
            retryreq.dont_filter = True
            retryreq.priority = request.priority + self.priority_adjust

            if isinstance(reason, Exception):
                reason = retry.global_object_name(reason.__class__)

            stats.inc_value("retry/count")
            stats.inc_value("retry/reason_count/%s" % reason)
            return retryreq
        else:
            stats.inc_value("retry/max_reached")
            logger.error(
                "Gave up retrying %(request)s (failed %(retries)d times): %(reason)s",
                {"request": request, "retries": retries, "reason": reason},
                extra={"spider": spider},
            )
            with open(self.log_path, "a+", encoding="utf-8") as f:
                f.write(request.url + "\n")
