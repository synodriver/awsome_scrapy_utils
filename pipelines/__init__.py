# -*- coding: utf-8 -*-
from .aria2 import Aria2Pipeline
from .json import JsonPipeline
from .mongodb import MongoDBPipeline
from .sql import SqlPipeline
from .text import TextPipeline

__all__ = ["Aria2Pipeline", "JsonPipeline", "MongoDBPipeline", "SqlPipeline", "TextPipeline"]
__author__ = "synodriver"
