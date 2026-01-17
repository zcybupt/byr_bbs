from byr_bbs.middlewares.resources import PROXY_LIST
import random


class RandomProxy(object):
    def process_request(self, request, spider):
        # proxy = random.choice(PROXY_LIST)
        # request.meta['proxy'] = 'http://%s' % proxy
        pass
