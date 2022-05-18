# -*- coding: utf-8 -*-
import scrapy
from scrapy.exporters import JsonLinesItemExporter


class JsonPipeline:
    """
    保存为json文件的pipeline
    需要添加settings.py
    JSON_PATH
    """

    def __init__(self, path: str):
        self.path = path
        self.file = None
        self.exporter: JsonLinesItemExporter = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.get("JSON_PATH"))

    def open_spider(self, spider: scrapy.Spider):
        self.file = open(self.path, "wb+")
        self.exporter = JsonLinesItemExporter(self.file)
        self.exporter.start_exporting()

    def close_spider(self, spider: scrapy.Spider):
        self.exporter.finish_exporting()
        self.file.close()

    def process_item(self, item, spider):
        self.exporter.export_item(item)
        return item
