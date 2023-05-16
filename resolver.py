import asyncio
import json
import re
import socket
from typing import List, Optional

import aiodns
import aiohttp
import scrapy.crawler
from scrapy.resolver import CachingThreadedResolver, dnscache
from scrapy.utils.defer import deferred_from_coro
from twisted.internet.interfaces import IResolverSimple
from zope.interface.declarations import implementer


@implementer(IResolverSimple)
class CachingAsyncResolver(CachingThreadedResolver):
    """
    Async caching resolver. Require aiodns
    """

    def __init__(
        self,
        reactor,
        cache_size,
        timeout,
        nameservers: Optional[List[str]] = None,
        **kwargs,
    ):
        super().__init__(reactor, cache_size, timeout)
        self._resolver = aiodns.DNSResolver(nameservers, None, **kwargs)

    @classmethod
    def from_crawler(cls, crawler: scrapy.crawler.Crawler, reactor):
        if crawler.settings.getbool("DNSCACHE_ENABLED"):
            cache_size = crawler.settings.getint("DNSCACHE_SIZE")
        else:
            cache_size = 0
        return cls(
            reactor,
            cache_size,
            crawler.settings.getfloat("DNS_TIMEOUT"),
            crawler.settings.getlist("AIODNS_NAMESERVERS", None),
            **crawler.settings.getdict("AIODNS_KW", {}),
        )

    def getHostByName(self, name, timeout=None):
        print(f"resolving name {name}")
        return deferred_from_coro(self._getHostByName(name, timeout))

    async def _getHostByName(self, name, timeout=None):
        if name in dnscache:
            return dnscache[name]
        try:
            resp = await asyncio.wait_for(
                self._resolver.gethostbyname(name, socket.AF_INET), timeout
            )
            result = resp.addresses[0]
            self._cache_result(result, name)
            return result
        except asyncio.TimeoutError:
            raise
        except aiodns.error.DNSError as exc:
            msg = exc.args[1] if len(exc.args) >= 1 else "DNS lookup failed"
            raise OSError(msg) from exc


@implementer(IResolverSimple)
class CachingAsyncDohResolver(CachingThreadedResolver):
    """
    Doh resolver
    """

    def __init__(self, reactor, cache_size, timeout, endpoints: List[str] = None):
        super().__init__(reactor, cache_size, timeout)

        self.endpoints = (
            [
                "https://1.0.0.1/dns-query",
                "https://1.1.1.1/dns-query",
                "https://[2606:4700:4700::1001]/dns-query",
                "https://[2606:4700:4700::1111]/dns-query",
                "https://cloudflare-dns.com/dns-query",
            ]
            if not endpoints
            else endpoints
        )
        self._client_session = aiohttp.ClientSession()

    @classmethod
    def from_crawler(cls, crawler, reactor):
        if crawler.settings.getbool("DNSCACHE_ENABLED"):
            cache_size = crawler.settings.getint("DNSCACHE_SIZE")
        else:
            cache_size = 0
        return cls(
            reactor,
            cache_size,
            crawler.settings.getfloat("DNS_TIMEOUT"),
            crawler.settings.getlist("DOH_ENDPOINTS", None),
        )

    def getHostByName(self, name, timeout=None):
        return deferred_from_coro(self._getHostByName(name, timeout))

    async def _getHostByName(self, name, timeout=None):
        if name in dnscache:
            return dnscache[name]
        done, pending = await asyncio.wait(
            [
                asyncio.create_task(
                    self._resolve(endpoint, name, socket.AF_INET, timeout)
                )
                for endpoint in self.endpoints
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        first_task = done.pop()
        ips = first_task.result()
        result = ips[0]
        self._cache_result(result, name)
        return result

    async def _resolve(self, endpoint, hostname, family, timeout=5) -> List[str]:
        params = {
            "name": hostname,
            "type": "AAAA" if family == socket.AF_INET6 else "A",
            "do": "false",
            "cd": "false",
        }

        async with self._client_session.get(
            endpoint,
            params=params,
            headers={"accept": "application/dns-json"},
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            if resp.status == 200:
                return self._parse_result(hostname, await resp.text())
            else:
                raise Exception(
                    "Failed to resolve {} with {}: HTTP Status {}".format(
                        hostname, endpoint, resp.status
                    )
                )

    def _parse_result(self, hostname, response) -> List[str]:
        data = json.loads(response)
        if data["Status"] != 0:
            raise Exception("Failed to resolve {}".format(hostname))

        # Pattern to match IPv4 addresses
        pattern = re.compile(
            r"((\d|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\.){3}(1\d\d|2[0-4]\d|25[0-5]|[1-9]\d|\d)"
        )
        result = []

        for i in data["Answer"]:
            ip = i["data"]

            if pattern.match(ip) is not None:
                result.append(ip)

        return result
