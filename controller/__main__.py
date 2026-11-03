"""命令行入口：python -m controller --help。"""
import argparse
import json
from pathlib import Path

import pandas as pd

from data import Database, MySQLConfig
from . import RiskController


def main():
    parser = argparse.ArgumentParser(description='FRM DataFrame计算工作流')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('init-db')
    commands.add_parser('health')
    commands.add_parser('list-datasets')
    ingest = commands.add_parser('import-csv')
    ingest.add_argument('name')
    ingest.add_argument('path')
    ingest.add_argument('--parse-dates', nargs='*', default=[])
    compute = commands.add_parser('calculate')
    compute.add_argument('dataset_id')
    compute.add_argument('chapter', type=int)
    compute.add_argument('function')
    compute.add_argument('--options', help='JSON文件，键为parameters和preparation')
    result = commands.add_parser('get-run')
    result.add_argument('run_id')
    args = parser.parse_args()
    database = Database(MySQLConfig.load())
    if args.command == 'init-db':
        database.initialize()
        print(database.health())
        return
    if args.command == 'health':
        print(database.health())
        return
    with database.session() as repository:
        if args.command == 'list-datasets':
            print(repository.list_datasets().to_string(index=False))
        elif args.command == 'import-csv':
            frame = pd.read_csv(args.path, parse_dates=args.parse_dates)
            print(repository.save_dataset(args.name, frame, metadata={'source': str(Path(args.path).resolve())}))
        elif args.command == 'calculate':
            options = json.loads(Path(args.options).read_text(encoding='utf-8')) if args.options else {}
            print(RiskController(repository).calculate(args.dataset_id, args.chapter, args.function, **options))
        elif args.command == 'get-run':
            print(repository.load_calculation(args.run_id))


if __name__ == '__main__':
    main()
