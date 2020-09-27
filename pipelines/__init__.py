# -*- coding: utf-8 -*-
from .aria2 import Aria2Pipeline
from .json import JsonPipeline
from .mongodb import MongoDBPipeline
from .mysql import MysqlPipeline
from .text import TextPipeline

__all__ = ["Aria2Pipeline", "JsonPipeline", "MongoDBPipeline", "MysqlPipeline", "TextPipeline"]
__author__ = "synodriver"
