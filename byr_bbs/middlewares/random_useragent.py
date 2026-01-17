import random

from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware

from byr_bbs.middlewares.resources import USER_AGENT_LIST


class RandomUserAgent(UserAgentMiddleware):
    def process_request(self, request, spider):
        user_agent = random.choice(USER_AGENT_LIST)
        request.headers['User-Agent'] = user_agent
        print(request.url)
