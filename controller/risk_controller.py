"""编排层不实现教材公式；事务由调用方Database.session控制。"""
from dataclasses import dataclass
import inspect

from service import load_chapter, source_fingerprint


@dataclass
class CalculationResult:
    value: object
    dataset_id: str
    run_id: str | None


class RiskController:
    def __init__(self, repository):
        self.repository = repository

    def calculate(self, dataset_id, chapter, function, parameters=None,
                  preparation=None, save=True):
        """调用以DataFrame为首参数的章节函数；类组合使用run。"""
        module = load_chapter(chapter)
        calculator = getattr(module, function)
        if function.startswith('_') or not inspect.isfunction(calculator) or calculator.__module__ != module.__name__:
            raise ValueError('Choose a public calculator function defined in this chapter')
        return self.run(dataset_id, f'Chapter{chapter}.{function}', calculator,
                        parameters, preparation, save)

    def run(self, dataset_id, operation, calculator, parameters=None,
            preparation=None, save=True):
        """calculator(df, **parameters)可组合类；operation是调用方提供的可读名称。

        自定义调用只记录名称和参数，不序列化Python函数；重放需调用方保留组合代码。
        preparation支持rename、sort_by、dropna_columns，均须显式指定。
        """
        parameters = dict(parameters or {})
        preparation = dict(preparation or {})
        unknown = preparation.keys() - {'rename', 'sort_by', 'dropna_columns'}
        if unknown:
            raise ValueError(f'Unknown preparation options: {sorted(unknown)}')
        snapshot = self.repository.load_dataset(dataset_id)
        frame = snapshot.frame.copy(deep=True)
        if preparation.get('rename'):
            frame = frame.rename(columns=preparation['rename'], errors='raise')
        if preparation.get('sort_by'):
            frame = frame.sort_values(preparation['sort_by'], kind='stable')
        if preparation.get('dropna_columns'):
            frame = frame.dropna(subset=preparation['dropna_columns'])
        value = calculator(frame, **parameters)
        run_id = None
        if save:
            run_id = self.repository.save_calculation(
                dataset_id, operation,
                {'calculation': parameters, 'preparation': preparation,
                 'input_rows': len(snapshot.frame), 'prepared_rows': len(frame)},
                value, source_fingerprint())
        return CalculationResult(value, dataset_id, run_id)
