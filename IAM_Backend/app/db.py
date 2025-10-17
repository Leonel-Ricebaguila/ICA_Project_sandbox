from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from .config import cfg

engine = create_engine(
    cfg.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in cfg.DATABASE_URL else {}
)

SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))
Base = declarative_base()

def db_session():
    # helper para usar con with db_session() as db:
    class _Ctx:
        def __enter__(self): self.db = SessionLocal(); return self.db
        def __exit__(self, exc_type, exc, tb): self.db.close()
    return _Ctx()
