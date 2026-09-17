from pathlib import Path
from sqlalchemy import create_engine,inspect,text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT=Path(__file__).resolve().parent.parent
DATA_DIR=ROOT/"data"; DATA_DIR.mkdir(exist_ok=True)
DATABASE_URL=f"sqlite:///{(DATA_DIR/'pos.db').as_posix()}"
engine=create_engine(DATABASE_URL,connect_args={"check_same_thread":False})
SessionLocal=sessionmaker(bind=engine,autoflush=False,expire_on_commit=False)

class Base(DeclarativeBase): pass

def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()

def init_db():
    from app import models
    Base.metadata.create_all(engine)
    columns={column["name"] for column in inspect(engine).get_columns("dining_table_items")}
    if "added_at" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE dining_table_items ADD COLUMN added_at DATETIME"))
            connection.execute(text("UPDATE dining_table_items SET added_at = CURRENT_TIMESTAMP WHERE added_at IS NULL"))
    sale_columns={column["name"] for column in inspect(engine).get_columns("sales")}
    with engine.begin() as connection:
        if "tip_amount" not in sale_columns: connection.execute(text("ALTER TABLE sales ADD COLUMN tip_amount NUMERIC(12,2) NOT NULL DEFAULT 0"))
        if "tip_method" not in sale_columns: connection.execute(text("ALTER TABLE sales ADD COLUMN tip_method VARCHAR(20)"))
        if "guest_count" not in sale_columns: connection.execute(text("ALTER TABLE sales ADD COLUMN guest_count INTEGER NOT NULL DEFAULT 0"))
        if "service_charge_percent" not in sale_columns: connection.execute(text("ALTER TABLE sales ADD COLUMN service_charge_percent INTEGER NOT NULL DEFAULT 0"))
        if "discount_amount" not in sale_columns: connection.execute(text("ALTER TABLE sales ADD COLUMN discount_amount NUMERIC(12,2) NOT NULL DEFAULT 0"))
        if "discount_reason" not in sale_columns: connection.execute(text("ALTER TABLE sales ADD COLUMN discount_reason VARCHAR(240) NOT NULL DEFAULT ''"))
    cash_columns={column["name"] for column in inspect(engine).get_columns("cash_sessions")}
    with engine.begin() as connection:
        if "declared_cash" not in cash_columns: connection.execute(text("ALTER TABLE cash_sessions ADD COLUMN declared_cash NUMERIC(12,2)"))
        if "declared_card" not in cash_columns: connection.execute(text("ALTER TABLE cash_sessions ADD COLUMN declared_card NUMERIC(12,2)"))
        if "declared_transfer" not in cash_columns: connection.execute(text("ALTER TABLE cash_sessions ADD COLUMN declared_transfer NUMERIC(12,2)"))
        if "reopened_count" not in cash_columns: connection.execute(text("ALTER TABLE cash_sessions ADD COLUMN reopened_count INTEGER NOT NULL DEFAULT 0"))
        if "last_reopened_at" not in cash_columns: connection.execute(text("ALTER TABLE cash_sessions ADD COLUMN last_reopened_at DATETIME"))
        if "last_reopened_by" not in cash_columns: connection.execute(text("ALTER TABLE cash_sessions ADD COLUMN last_reopened_by VARCHAR(120) NOT NULL DEFAULT ''"))
        if "last_reopen_reason" not in cash_columns: connection.execute(text("ALTER TABLE cash_sessions ADD COLUMN last_reopen_reason VARCHAR(240) NOT NULL DEFAULT ''"))
    table_columns={column["name"] for column in inspect(engine).get_columns("dining_tables")}
    with engine.begin() as connection:
        if "guest_count" not in table_columns: connection.execute(text("ALTER TABLE dining_tables ADD COLUMN guest_count INTEGER NOT NULL DEFAULT 0"))
        if "assigned_waiter_id" not in table_columns: connection.execute(text("ALTER TABLE dining_tables ADD COLUMN assigned_waiter_id INTEGER"))
        if "assigned_waiter_name" not in table_columns: connection.execute(text("ALTER TABLE dining_tables ADD COLUMN assigned_waiter_name VARCHAR(120) NOT NULL DEFAULT ''"))
        if "cash_session_id" not in table_columns: connection.execute(text("ALTER TABLE dining_tables ADD COLUMN cash_session_id INTEGER"))
    permission_columns={column["name"] for column in inspect(engine).get_columns("permission_config")}
    table_columns={column["name"] for column in inspect(engine).get_columns("dining_tables")}
    with engine.begin() as connection:
        if "account_printed_at" not in table_columns: connection.execute(text("ALTER TABLE dining_tables ADD COLUMN account_printed_at DATETIME"))
        if "print_on_checkout" not in permission_columns: connection.execute(text("ALTER TABLE permission_config ADD COLUMN print_on_checkout BOOLEAN NOT NULL DEFAULT 1"))
        if "waiter_require_guest_count" not in permission_columns: connection.execute(text("ALTER TABLE permission_config ADD COLUMN waiter_require_guest_count BOOLEAN NOT NULL DEFAULT 0"))
        if "developer_mode" not in permission_columns: connection.execute(text("ALTER TABLE permission_config ADD COLUMN developer_mode BOOLEAN NOT NULL DEFAULT 0"))
        if "cashier_discount_mode" not in permission_columns: connection.execute(text("ALTER TABLE permission_config ADD COLUMN cashier_discount_mode VARCHAR(20) NOT NULL DEFAULT 'allowed'"))
        if "waiter_reopen_printed_table" not in permission_columns: connection.execute(text("ALTER TABLE permission_config ADD COLUMN waiter_reopen_printed_table BOOLEAN NOT NULL DEFAULT 0"))
        if "cashier_reopen_printed_table" not in permission_columns: connection.execute(text("ALTER TABLE permission_config ADD COLUMN cashier_reopen_printed_table BOOLEAN NOT NULL DEFAULT 1"))
        if "waiter_reprint_account" not in permission_columns: connection.execute(text("ALTER TABLE permission_config ADD COLUMN waiter_reprint_account BOOLEAN NOT NULL DEFAULT 1"))
        if "cashier_reprint_account" not in permission_columns: connection.execute(text("ALTER TABLE permission_config ADD COLUMN cashier_reprint_account BOOLEAN NOT NULL DEFAULT 1"))
        if "waiter_product_transfer_mode" not in permission_columns: connection.execute(text("ALTER TABLE permission_config ADD COLUMN waiter_product_transfer_mode VARCHAR(20) NOT NULL DEFAULT 'allowed'"))
        if "cashier_product_transfer_mode" not in permission_columns: connection.execute(text("ALTER TABLE permission_config ADD COLUMN cashier_product_transfer_mode VARCHAR(20) NOT NULL DEFAULT 'allowed'"))
        if "waiter_table_transfer_mode" not in permission_columns: connection.execute(text("ALTER TABLE permission_config ADD COLUMN waiter_table_transfer_mode VARCHAR(20) NOT NULL DEFAULT 'allowed'"))
        if "cashier_table_transfer_mode" not in permission_columns: connection.execute(text("ALTER TABLE permission_config ADD COLUMN cashier_table_transfer_mode VARCHAR(20) NOT NULL DEFAULT 'allowed'"))
        if "cancel_password_hash" not in permission_columns: connection.execute(text("ALTER TABLE permission_config ADD COLUMN cancel_password_hash VARCHAR(512) NOT NULL DEFAULT ''"))
        if "transfer_password_hash" not in permission_columns: connection.execute(text("ALTER TABLE permission_config ADD COLUMN transfer_password_hash VARCHAR(512) NOT NULL DEFAULT ''"))
        if "product_transfer_password_hash" not in permission_columns: connection.execute(text("ALTER TABLE permission_config ADD COLUMN product_transfer_password_hash VARCHAR(512) NOT NULL DEFAULT ''"))
        if "table_transfer_password_hash" not in permission_columns: connection.execute(text("ALTER TABLE permission_config ADD COLUMN table_transfer_password_hash VARCHAR(512) NOT NULL DEFAULT ''"))
        if "discount_password_hash" not in permission_columns: connection.execute(text("ALTER TABLE permission_config ADD COLUMN discount_password_hash VARCHAR(512) NOT NULL DEFAULT ''"))
        if "service_charge_percent" not in permission_columns: connection.execute(text("ALTER TABLE permission_config ADD COLUMN service_charge_percent INTEGER NOT NULL DEFAULT 10"))
        connection.execute(text("UPDATE permission_config SET include_suggested_tip = 0 WHERE include_tip_in_ticket = 1 AND include_suggested_tip = 1"))
