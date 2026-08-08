"""数据库初始化脚本 — 使用 SQLAlchemy ORM 自动建表（兼容 SQLite / MySQL）"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import engine, Base
from models.tables import *  # 导入所有 ORM 模型（Enterprise, EnterpriseBusiness, Measurement, DataSource, ModelMetric）

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("所有数据库表创建成功！")
