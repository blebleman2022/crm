import os
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen

import pytest
from werkzeug.security import generate_password_hash


ROOT_DIR = Path(__file__).resolve().parents[2]
VENV_PYTHON = ROOT_DIR / "venv" / "bin" / "python3"

TEST_PRIVATE_MANAGER_PHONE = "13900139998"
TEST_PRIVATE_MANAGER_NAME = "Playwright私域经理"
TEST_PRIVATE_STUDENT = "PWTEST私域学员"
TEST_PUBLIC_STUDENT = "PWTEST公域学员"
TEST_PRIVATE_PARENT_WECHAT = "pwtest_private_parent"
TEST_PUBLIC_PARENT_WECHAT = "pwtest_public_parent"


def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _resolve_python_bin():
    """Resolve Python executable for spawning the app server."""
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    system_python = shutil.which("python3")
    if not system_python:
        raise RuntimeError("未找到可用的 python3 可执行文件")
    return system_python


def _ensure_user(conn, username, phone, role, is_private_owner=0):
    row = conn.execute("SELECT id FROM users WHERE phone = ?", (phone,)).fetchone()
    now = _now_str()
    password_hash = generate_password_hash("123456", method="pbkdf2:sha256")
    if row:
        user_id = row[0]
        try:
            conn.execute(
                """
                UPDATE users
                SET username = ?, role = ?, status = 1, is_private_owner = ?,
                    password_hash = ?, must_change_password = 0, password_changed_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (username, role, is_private_owner, password_hash, now, now, user_id),
            )
        except sqlite3.OperationalError:
            conn.execute(
                """
                UPDATE users
                SET username = ?, role = ?, status = 1, is_private_owner = ?, updated_at = ?
                WHERE id = ?
                """,
                (username, role, is_private_owner, now, user_id),
            )
        return user_id

    try:
        cursor = conn.execute(
            """
            INSERT INTO users (
                username, phone, role, status, created_at, updated_at, is_private_owner,
                password_hash, must_change_password, password_changed_at
            )
            VALUES (?, ?, ?, 1, ?, ?, ?, ?, 0, ?)
            """,
            (username, phone, role, now, now, is_private_owner, password_hash, now),
        )
    except sqlite3.OperationalError:
        cursor = conn.execute(
            """
            INSERT INTO users (username, phone, role, status, created_at, updated_at, is_private_owner)
            VALUES (?, ?, ?, 1, ?, ?, ?)
            """,
            (username, phone, role, now, now, is_private_owner),
        )
    return cursor.lastrowid


def _ensure_test_lead(
    conn,
    *,
    student_name,
    parent_display_name,
    parent_wechat_name,
    sales_user_id,
    scope,
    private_owner_id,
):
    row = conn.execute(
        "SELECT id FROM leads WHERE parent_wechat_name = ?",
        (parent_wechat_name,),
    ).fetchone()

    first_payment_dt = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
    now = _now_str()

    if row:
        lead_id = row[0]
        conn.execute(
            """
            UPDATE leads
            SET student_name = ?, parent_wechat_display_name = ?, sales_user_id = ?, stage = ?,
                grade = ?, lead_source = ?, customer_scope = ?, private_owner_id = ?,
                first_payment_at = ?, deposit_paid_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                student_name,
                parent_display_name,
                sales_user_id,
                "首笔支付",
                "高二",
                "Playwright测试",
                scope,
                private_owner_id,
                first_payment_dt,
                first_payment_dt,
                now,
                lead_id,
            ),
        )
        return lead_id

    cursor = conn.execute(
        """
        INSERT INTO leads (
            student_name, parent_wechat_display_name, parent_wechat_name,
            lead_source, grade, sales_user_id, stage,
            first_payment_at, deposit_paid_at, created_at, updated_at,
            customer_scope, private_owner_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            student_name,
            parent_display_name,
            parent_wechat_name,
            "Playwright测试",
            "高二",
            sales_user_id,
            "首笔支付",
            first_payment_dt,
            first_payment_dt,
            now,
            now,
            scope,
            private_owner_id,
        ),
    )
    return cursor.lastrowid


def _ensure_payment(conn, lead_id):
    row = conn.execute("SELECT id FROM payments WHERE lead_id = ?", (lead_id,)).fetchone()
    pay_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    now = _now_str()
    if row:
        conn.execute(
            """
            UPDATE payments
            SET amount = 1000, payment_date = ?, payment_notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (pay_date, "Playwright首笔支付", now, row[0]),
        )
        return

    conn.execute(
        """
        INSERT INTO payments (lead_id, amount, payment_date, payment_notes, created_at, updated_at)
        VALUES (?, 1000, ?, ?, ?, ?)
        """,
        (lead_id, pay_date, "Playwright首笔支付", now, now),
    )


def _ensure_test_customer(
    conn,
    *,
    lead_id,
    sales_user_id,
    supervisor_user_id,
    scope,
    private_owner_id,
):
    row = conn.execute("SELECT id FROM customers WHERE lead_id = ?", (lead_id,)).fetchone()
    now = _now_str()
    if row:
        customer_id = row[0]
        conn.execute(
            """
            UPDATE customers
            SET sales_user_id = ?, supervisor_user_id = ?, tutor_user_id = NULL, payment_amount = 10000,
                award_requirement = '无', service_type = 'tutoring', exam_year = 2027,
                customer_scope = ?, private_owner_id = ?, phase = 'service_delivery', updated_at = ?
            WHERE id = ?
            """,
            (sales_user_id, supervisor_user_id, scope, private_owner_id, now, customer_id),
        )
        return customer_id

    cursor = conn.execute(
        """
        INSERT INTO customers (
            lead_id, sales_user_id, supervisor_user_id, tutor_user_id, payment_amount,
            award_requirement, service_type, exam_year,
            converted_at, created_at, updated_at, customer_scope, private_owner_id, phase
        ) VALUES (?, ?, ?, NULL, 10000, '无', 'tutoring', 2027, ?, ?, ?, ?, ?, 'service_delivery')
        """,
        (lead_id, sales_user_id, supervisor_user_id, now, now, now, scope, private_owner_id),
    )
    return cursor.lastrowid


def _ensure_customer_payment(conn, *, customer_id, supervisor_user_id, scope_snapshot):
    row = conn.execute("SELECT id FROM customer_payments WHERE customer_id = ?", (customer_id,)).fetchone()
    pay_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    now = _now_str()
    if row:
        conn.execute(
            """
            UPDATE customer_payments
            SET supervisor_user_id = ?, total_amount = 10000, first_payment = 3000,
                first_payment_date = ?, scope_snapshot = ?, updated_at = ?
            WHERE id = ?
            """,
            (supervisor_user_id, pay_date, scope_snapshot, now, row[0]),
        )
        return

    conn.execute(
        """
        INSERT INTO customer_payments (
            customer_id, supervisor_user_id, total_amount,
            first_payment, first_payment_date, scope_snapshot, created_at, updated_at
        ) VALUES (?, ?, 10000, 3000, ?, ?, ?, ?)
        """,
        (customer_id, supervisor_user_id, pay_date, scope_snapshot, now, now),
    )


def _seed_test_data(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    # 班主任（若不存在则创建）
    teacher_row = conn.execute(
        "SELECT id, phone FROM users WHERE role = 'teacher_supervisor' AND status = 1 ORDER BY id LIMIT 1"
    ).fetchone()
    if teacher_row:
        teacher_id = teacher_row[0]
        teacher_phone = teacher_row[1]
    else:
        teacher_phone = "13900139996"
        teacher_id = _ensure_user(conn, "Playwright班主任", teacher_phone, "teacher_supervisor")

    # 普通销售管理（公域）
    manager_row = conn.execute(
        """
        SELECT id, phone FROM users
        WHERE role = 'sales_manager' AND status = 1 AND COALESCE(is_private_owner, 0) = 0
        ORDER BY id
        LIMIT 1
        """
    ).fetchone()
    if manager_row:
        public_manager_id = manager_row[0]
        public_manager_phone = manager_row[1]
    else:
        public_manager_phone = "13900139997"
        public_manager_id = _ensure_user(conn, "Playwright销售管理", public_manager_phone, "sales_manager", 0)

    # 私域负责人（销售管理）
    private_manager_id = _ensure_user(
        conn,
        TEST_PRIVATE_MANAGER_NAME,
        TEST_PRIVATE_MANAGER_PHONE,
        "sales_manager",
        1,
    )

    private_lead_id = _ensure_test_lead(
        conn,
        student_name=TEST_PRIVATE_STUDENT,
        parent_display_name="PWTEST私域家长",
        parent_wechat_name=TEST_PRIVATE_PARENT_WECHAT,
        sales_user_id=private_manager_id,
        scope="private",
        private_owner_id=private_manager_id,
    )
    _ensure_payment(conn, private_lead_id)
    private_customer_id = _ensure_test_customer(
        conn,
        lead_id=private_lead_id,
        sales_user_id=private_manager_id,
        supervisor_user_id=teacher_id,
        scope="private",
        private_owner_id=private_manager_id,
    )
    _ensure_customer_payment(
        conn,
        customer_id=private_customer_id,
        supervisor_user_id=teacher_id,
        scope_snapshot="private",
    )

    public_lead_id = _ensure_test_lead(
        conn,
        student_name=TEST_PUBLIC_STUDENT,
        parent_display_name="PWTEST公域家长",
        parent_wechat_name=TEST_PUBLIC_PARENT_WECHAT,
        sales_user_id=public_manager_id,
        scope="public",
        private_owner_id=None,
    )
    _ensure_payment(conn, public_lead_id)
    public_customer_id = _ensure_test_customer(
        conn,
        lead_id=public_lead_id,
        sales_user_id=public_manager_id,
        supervisor_user_id=teacher_id,
        scope="public",
        private_owner_id=None,
    )
    _ensure_customer_payment(
        conn,
        customer_id=public_customer_id,
        supervisor_user_id=teacher_id,
        scope_snapshot="public",
    )

    conn.commit()
    conn.close()

    return {
        "phones": {
            "private_manager": TEST_PRIVATE_MANAGER_PHONE,
            "public_manager": public_manager_phone,
            "teacher_supervisor": teacher_phone,
        },
        "private_owner_id": private_manager_id,
        "customers": {
            "private_customer_id": private_customer_id,
            "public_customer_id": public_customer_id,
        },
        "students": {
            "private": TEST_PRIVATE_STUDENT,
            "public": TEST_PUBLIC_STUDENT,
        },
    }


def _wait_for_server(base_url, timeout_sec=45):
    health_url = f"{base_url}/health"
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urlopen(health_url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"服务器未在 {timeout_sec}s 内就绪: {health_url}")


@pytest.fixture(scope="session")
def e2e_env():
    temp_dir = Path(tempfile.mkdtemp(prefix="crm_playwright_"))
    source_db = ROOT_DIR / "instance" / "edu_crm.db"
    test_db = temp_dir / "edu_crm_e2e.db"
    shutil.copy2(source_db, test_db)

    seeded = _seed_test_data(test_db)
    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{test_db}"
    env["PORT"] = str(port)
    env["FLASK_ENV"] = "development"
    env["PYTHONUNBUFFERED"] = "1"

    log_file_path = temp_dir / "server.log"
    log_handle = open(log_file_path, "w", encoding="utf-8")

    server_cmd = [
        _resolve_python_bin(),
        "-c",
        (
            "import os;"
            "from run import create_app, init_database;"
            "app=create_app('development');"
            "init_database(app);"
            "app.run(host='127.0.0.1', port=int(os.environ['PORT']), debug=False, use_reloader=False)"
        ),
    ]

    server_proc = subprocess.Popen(
        server_cmd,
        cwd=ROOT_DIR,
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )

    try:
        _wait_for_server(base_url)
    except Exception as exc:
        log_handle.flush()
        try:
            with open(log_file_path, "r", encoding="utf-8") as f:
                server_log = f.read()
        except Exception:
            server_log = "<无法读取服务日志>"
        server_proc.terminate()
        raise RuntimeError(f"{exc}\n--- server log ---\n{server_log}") from exc

    yield {
        "base_url": base_url,
        "phones": seeded["phones"],
        "private_owner_id": seeded["private_owner_id"],
        "customers": seeded["customers"],
        "students": seeded["students"],
    }

    server_proc.terminate()
    try:
        server_proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        server_proc.kill()
        server_proc.wait(timeout=5)
    log_handle.close()
    shutil.rmtree(temp_dir, ignore_errors=True)
