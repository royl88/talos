# coding=utf-8
import warnings

import pytest

from talos.core import config

CONF = {
    "level_1": {
        "level_1.level_2": "not variable",
        "items": "reserved function",
        "1bac": {
            "a": {
                "2abc": {
                    "b": True
                }
            }
        },
        "ok": {
            "secret": "you got it"
        }
    }
}


def test_init_warnings():
    warnings.simplefilter("always")
    with warnings.catch_warnings(record=True) as ws:
        config.Config(CONF, check_reserved=True)
        for w in ws:
            print(w.message)
        assert (len(ws) == 4)


def test_set_options_warnings():
    warnings.simplefilter("always")
    with warnings.catch_warnings(record=True) as ws:
        c = config.Config(None)
        c.set_options(CONF, check_reserved=True)
        for w in ws:
            print(w.message)
        assert (len(ws) == 4)


def test_call_warnings():
    warnings.simplefilter("always")
    with warnings.catch_warnings(record=True) as ws:
        c = config.Config(None)
        c(CONF, check_reserved=True)
        for w in ws:
            print(w.message)
        assert (len(ws) == 4)


def test_access():
    c = config.Config(CONF)
    assert (c.level_1.ok.secret == "you got it")
    assert (c.level_1['level_1.level_2'] == "not variable")
    assert (c.level_1['items'] == "reserved function")
    assert (c.level_1['1bac'].a['2abc'].b is True)
    assert (c.level_1.ok.secret == "you got it")


def test_exception():
    c = config.Config(CONF)
    with pytest.raises(KeyError):
        c.level_1['1bac'].a['noopts']
    with pytest.raises(AttributeError):
        c.level_1['1bac'].a['2abc'].c
