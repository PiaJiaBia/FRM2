"""python -m api init-db；python -m api（本机8000端口，单进程任务管理）。"""
import argparse

from data import Database, MySQLConfig
from data.workbench_repository import initialize_workbench


def main():
    parser = argparse.ArgumentParser(description='FRM本机HTTP服务')
    parser.add_argument('command', choices=['serve', 'init-db'], default='serve', nargs='?')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    database = Database(MySQLConfig.load())
    if args.command == 'init-db':
        initialize_workbench(database)
        print(database.health())
    else:
        import uvicorn
        from .main import create_app
        uvicorn.run(create_app(database), host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
