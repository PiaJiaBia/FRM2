"""连接配置、数据库初始化和事务生命周期。密码不出现在对象repr中。"""
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
import os
import re
import tomllib

import pymysql

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class MySQLConfig:
    host: str
    user: str
    password: str = field(repr=False)
    port: int = 3306
    database: str = 'FRM'
    connect_timeout: int = 5

    @classmethod
    def load(cls, path=None):
        """环境变量FRM_MYSQL_*优先；默认本机配置config/mysql.local.toml。"""
        path = Path(path) if path else ROOT / 'config/mysql.local.toml'
        settings = tomllib.loads(path.read_text(encoding='utf-8')).get('mysql', {}) if path.exists() else {}
        for name in cls.__dataclass_fields__:
            value = os.environ.get('FRM_MYSQL_' + name.upper())
            if value is not None:
                settings[name] = int(value) if name in ('port', 'connect_timeout') else value
        return cls(**settings)


class Database:
    def __init__(self, config):
        self.config = config

    def connect(self, select_database=True):
        c = self.config
        return pymysql.connect(host=c.host, port=c.port, user=c.user, password=c.password,
            database=c.database if select_database else None, charset='utf8mb4',
            connect_timeout=c.connect_timeout, read_timeout=30, write_timeout=30,
            autocommit=False, cursorclass=pymysql.cursors.DictCursor,
            init_command="SET time_zone = '+00:00'")

    def initialize(self):
        """显式初始化，不在连接/计算时偷偷建表；只CREATE IF NOT EXISTS，不删改旧数据。"""
        name = self.config.database
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name):
            raise ValueError('Invalid database identifier')
        connection = self.connect(select_database=False)
        try:
            with connection.cursor() as cursor:
                cursor.execute(f'CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
            connection.select_db(name)
            with connection.cursor() as cursor:
                for statement in (Path(__file__).parent / 'schema.sql').read_text(encoding='utf-8').split(';'):
                    if statement.strip():
                        cursor.execute(statement)
            connection.commit()
        finally:
            connection.close()

    @contextmanager
    def session(self, rollback=False):
        """一个controller工作流一个事务；出错回滚。rollback=True供不留测试数据的验证。"""
        from .repository import Repository
        connection = self.connect()
        try:
            yield Repository(connection)
            connection.rollback() if rollback else connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def health(self):
        with self.session() as repository:
            with repository.connection.cursor() as cursor:
                cursor.execute('SELECT DATABASE() AS database_name, VERSION() AS server_version')
                result = cursor.fetchone()
                cursor.execute('SELECT MAX(version) AS schema_version FROM frm_schema_versions')
                result.update(cursor.fetchone())
                return result
