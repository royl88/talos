# coding=utf-8
"""
本模块提供i18n国际化功能

"""

from __future__ import absolute_import

import collections
import gettext
import logging
from talos.core import utils

LOG = logging.getLogger(__name__)


class Translator():
    """
    i18n国际化翻译器

    用户可以调用setup来更改当前locale
    """

    def __init__(self):
        self.default_language = None
        self._translation_maps = collections.OrderedDict()

    def __call__(self, value):
        if self._translation_maps and self.default_language:
            return self._translation_maps[self.default_language].gettext(value)
        else:
            return value

    def setup(self, app, locales, lang):
        # 清除成员信息以支持多次初始化
        self.default_language = None
        self._translation_maps = collections.OrderedDict()
        if utils.is_list_type(lang):
            if len(lang) == 0:
                LOG.warning('language(%s) files not found, no translation will be used', lang)
            for l in lang:
                find_mo = gettext.find(app,
                                    localedir=locales,
                                    languages=[l])
                if find_mo:
                    # 加载所有指定语言 & 设置第一个有效mo文件的语言为默认语言
                    with open(find_mo, 'rb') as f:
                        self._translation_maps[l] = gettext.GNUTranslations(f)
                    if self.default_language is None:
                        self.default_language = l
        else:
            self.default_language = lang
            try:
                self._translation_maps[lang] = gettext.translation(app, locales, [lang])
            except IOError:
                LOG.warning('language(%s) files not found, no translation will be used', lang)

    def change(self, lang):
        # 更改默认翻译语言
        if lang in self.available_languages:
            self.default_language = lang
            return True
        else:
            return False

    @property
    def available_languages(self):
        return list(self._translation_maps.keys())
    
    def client_prefers(self, accept, supported=None):

        def parse_language_range(language):
            lang, params = '', {}
            language_opts = language.split(';')
            language_opts = [i.strip() for i in language_opts if i.strip()]
            if len(language_opts) > 1:
                lang = language_opts[0]
                params['q'] = float(language_opts[1].lower().split('=')[1])
            else:
                lang = language_opts[0]
                params['q'] = 1.0
            return (lang, params)

        split_languages = [i.strip() for i in accept.split(',') if i.strip()]
        split_languages = [parse_language_range(i) for i in split_languages]
        split_languages = sorted(split_languages, key=lambda x: x[1]['q'], reverse=True)
        supported = supported or self.available_languages
        for lang in split_languages:
            if lang[0] in supported:
                return lang
        return None


_ = Translator()
