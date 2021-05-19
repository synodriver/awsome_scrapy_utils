# -*- coding: utf-8 -*-
from .aria2 import Aria2Pipeline
from .json import JsonPipeline
from .mongodb import AsyncMongoDBPipeline, DeferredMongoDBPipeline
from .sql import SqlPipeline
from .text import TextPipeline

__all__ = ["Aria2Pipeline", "JsonPipeline", "AsyncMongoDBPipeline", "DeferredMongoDBPipeline", "SqlPipeline",
           "TextPipeline"]
__author__ = "synodriver"
