"""显式注册已接入章节，网页不能按用户输入导入任意模块。"""
from functools import lru_cache
from importlib import import_module


@lru_cache
def groups():
    return tuple(import_module(f'controller.chapter_groups.{name}')
                 for name in ('risk', 'dependence', 'rates'))


def operations():
    return [item for group in groups() for item in group.operations()]


def examples():
    return [item for group in groups() for item in group.examples()]


def example_frame(identity):
    for group in groups():
        if any(item['id'] == identity for item in group.examples()):
            return group.example_frame(identity)
    raise ValueError('未知章节示例')


def calculate(df, metadata, request):
    for group in groups():
        if any(item['id'] == request['operation'] for item in group.operations()):
            return group.calculate(df, metadata, request)
    raise ValueError('未知网页计算操作')
