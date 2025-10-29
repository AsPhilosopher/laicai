from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional, Tuple

import mysql.connector
from mysql.connector import MySQLConnection


DB_CONFIG: Dict[str, Any] = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "Mysql654321!",
    "database": "test",
}


def get_connection() -> MySQLConnection:
    """获取数据库连接。"""
    return mysql.connector.connect(**DB_CONFIG)


def create_demo(record_id: int, name: Optional[str], money: Optional[float], birthday: Optional[datetime.datetime]) -> None:
    """新增一条 demo 记录。"""
    sql = (
        "INSERT INTO demo (id, name, money, birthday) VALUES (%s, %s, %s, %s)"
    )
    params: Tuple[Any, ...] = (record_id, name, money, birthday)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()


def get_demo_by_id(record_id: int) -> Optional[Dict[str, Any]]:
    """按 id 查询一条 demo 记录。"""
    sql = "SELECT id, name, money, birthday FROM demo WHERE id = %s"
    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(sql, (record_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def get_all_demos() -> List[Dict[str, Any]]:
    """查询所有 demo 记录。"""
    sql = "SELECT id, name, money, birthday FROM demo ORDER BY id"
    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            return [dict(r) for r in rows]


def update_demo(
    record_id: int,
    name: Optional[str] = None,
    money: Optional[float] = None,
    birthday: Optional[datetime.datetime] = None,
) -> int:
    """按 id 更新 demo 记录，返回受影响行数。

    仅更新提供了新值的字段。
    """
    set_clauses: List[str] = []
    params: List[Any] = []

    if name is not None:
        set_clauses.append("name = %s")
        params.append(name)
    if money is not None:
        set_clauses.append("money = %s")
        params.append(money)
    if birthday is not None:
        set_clauses.append("birthday = %s")
        params.append(birthday)

    if not set_clauses:
        return 0

    sql = f"UPDATE demo SET {', '.join(set_clauses)} WHERE id = %s"
    params.append(record_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
        conn.commit()
        return cur.rowcount  # type: ignore[name-defined]


def delete_demo(record_id: int) -> int:
    """按 id 删除 demo 记录，返回受影响行数。"""
    sql = "DELETE FROM demo WHERE id = %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (record_id,))
        conn.commit()
        return cur.rowcount  # type: ignore[name-defined]


def _print_records(title: str) -> None:
    print(f"\n=== {title} ===")
    for row in get_all_demos():
        print(row)


if __name__ == "__main__":
    # 演示用：请先确保已在 MySQL 中创建 demo 表且库名为 test
    # CREATE TABLE `demo` (
    #   `id` int NOT NULL,
    #   `name` varchar(45) DEFAULT NULL,
    #   `money` float DEFAULT NULL,
    #   `birthday` datetime DEFAULT NULL,
    #   PRIMARY KEY (`id`)
    # ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

    # 先删两个记录，避免id冲突
    delete_demo(2)
    delete_demo(3)

    # 1) 新增
    create_demo(
        record_id=2,
        name="Alice",
        money=100.5,
        birthday=datetime.datetime(1995, 5, 1, 8, 30, 0),
    )
    create_demo(
        record_id=3,
        name="Bob",
        money=250.0,
        birthday=datetime.datetime(1990, 10, 20, 12, 0, 0),
    )
    _print_records("插入两条后")

    # 2) 查询（按 id）
    one = get_demo_by_id(1)
    print("\n按 id=1 查询:", one)

    # 3) 更新（部分字段）
    affected = update_demo(1, money=199.99)
    print(f"\n更新 id=1 的 money，受影响行数: {affected}")
    _print_records("更新后")

    # 4) 删除
    deleted = delete_demo(2)
    print(f"\n删除 id=2，受影响行数: {deleted}")
    _print_records("删除后")
