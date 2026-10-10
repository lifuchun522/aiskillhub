import json

import db
from engine.flow_engine import FlowEngine

FLOW_CODE = "FLOW-CUSTOMER-APPROVAL"

_ROLE_STATUS = {
    "CUSTOMER_MANAGER": "待客户经理审批",
    "DEPT_GENERAL_MANAGER": "待部门总经理审批",
}

_REQUIRED = ["customer_name", "customer_type", "customer_level"]


def _validate(data):
    for field in _REQUIRED:
        if not data.get(field):
            raise ValueError("客户名称、客户类型、客户等级为必填项")


def _gen_customer_no():
    import datetime
    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    return "CUS" + now


def list_customers(page=1, size=10, filters=None):
    filters = filters or {}
    where = "WHERE 1=1"
    params = []
    if filters.get("customer_no"):
        where += " AND customer_no LIKE ?"
        params.append(f"%{filters['customer_no']}%")
    if filters.get("customer_name"):
        where += " AND customer_name LIKE ?"
        params.append(f"%{filters['customer_name']}%")
    if filters.get("status"):
        where += " AND status = ?"
        params.append(filters["status"])
    total = db.query_one(f"SELECT COUNT(*) AS c FROM customer_application {where}", params)["c"]
    rows = db.query(
        f"SELECT * FROM customer_application {where} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [size, (page - 1) * size],
    )
    return {"list": rows, "total": total, "page": page, "size": size}


def get_customer(customer_id):
    return db.query_one("SELECT * FROM customer_application WHERE id = ?", (customer_id,))


def create_draft(data, user):
    _validate(data)
    customer_no = data.get("customer_no") or _gen_customer_no()
    if db.query_one("SELECT id FROM customer_application WHERE customer_no = ?", (customer_no,)):
        raise ValueError("客户编号已存在")
    customer_id = db.execute(
        """
        INSERT INTO customer_application
            (customer_no, customer_name, customer_type, industry, contact_person, contact_phone,
             customer_level, address, remark, status, applicant_id, applicant_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '草稿', ?, ?)
        """,
        (
            customer_no, data["customer_name"], data["customer_type"], data.get("industry"),
            data.get("contact_person"), data.get("contact_phone"), data["customer_level"],
            data.get("address"), data.get("remark"), user["id"], user["real_name"],
        ),
    )[0]
    return get_customer(customer_id)


def update_draft(customer_id, data, user):
    customer = get_customer(customer_id)
    if not customer:
        raise ValueError("客户申请不存在")
    if customer["status"] not in ("草稿", "已驳回"):
        raise ValueError("仅草稿或已驳回状态可修改")
    _validate(data)
    db.execute(
        """
        UPDATE customer_application SET customer_name=?, customer_type=?, industry=?, contact_person=?,
            contact_phone=?, customer_level=?, address=?, remark=?, status='草稿', updated_at=CURRENT_TIMESTAMP
        WHERE id=?
        """,
        (
            data["customer_name"], data["customer_type"], data.get("industry"), data.get("contact_person"),
            data.get("contact_phone"), data["customer_level"], data.get("address"), data.get("remark"),
            customer_id,
        ),
    )
    return get_customer(customer_id)


def submit(customer_id, user):
    customer = get_customer(customer_id)
    if not customer:
        raise ValueError("客户申请不存在")
    if customer["status"] not in ("草稿", "已驳回"):
        raise ValueError("当前状态不可提交")

    def _do(conn):
        _validate(customer)
        definition = db.query_one(
            "SELECT * FROM flow_definition WHERE code = ? AND status = 1",
            (FLOW_CODE,),
            conn,
        )
        if not definition:
            raise ValueError("客户申请审批流程未发布")

        engine = FlowEngine(conn)
        instance_id = engine.start(
            definition["id"],
            customer["customer_no"],
            ["AGG-CUSTOMER-001"],
            {"customer_id": customer_id},
            user["id"],
        )
        db.execute(
            "UPDATE customer_application SET instance_id=?, status='待客户经理审批', applicant_id=?, applicant_name=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (instance_id, user["id"], user["real_name"], customer_id),
            conn,
        )
        return customer_id

    db.transaction(_do)
    return get_customer(customer_id)


def withdraw(customer_id, user):
    customer = get_customer(customer_id)
    if not customer:
        raise ValueError("客户申请不存在")
    if customer["status"] != "待客户经理审批":
        raise ValueError("仅待客户经理审批且未处理前可撤回")
    if not customer["instance_id"]:
        raise ValueError("流程实例不存在")

    def _do(conn):
        done = db.query_one(
            "SELECT COUNT(*) AS c FROM flow_task WHERE instance_id=? AND status IN ('DONE','CANCEL') AND action IS NOT NULL",
            (customer["instance_id"],),
            conn,
        )["c"]
        if done > 0:
            raise ValueError("审批人已处理，无法撤回")
        db.execute(
            "UPDATE flow_instance SET status='TERMINATED', ended_at=CURRENT_TIMESTAMP WHERE id=?",
            (customer["instance_id"],),
            conn,
        )
        db.execute(
            "UPDATE flow_task SET status='CANCEL' WHERE instance_id=? AND status='TODO'",
            (customer["instance_id"],),
            conn,
        )
        db.execute(
            "UPDATE customer_application SET status='草稿', instance_id=NULL, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (customer_id,),
            conn,
        )

    db.transaction(_do)
    return get_customer(customer_id)


def sync_status_from_instance(instance_id, conn):
    inst = db.query_one("SELECT * FROM flow_instance WHERE id = ?", (instance_id,), conn)
    if not inst:
        return None
    customer = db.query_one("SELECT * FROM customer_application WHERE instance_id = ?", (instance_id,), conn)
    if not customer:
        return None
    status = None
    if inst["status"] == "APPROVED":
        status = "已通过"
    elif inst["status"] == "REJECTED":
        status = "已驳回"
    elif inst["status"] == "RUNNING":
        todo = db.query_one(
            "SELECT * FROM flow_task WHERE instance_id=? AND status='TODO' ORDER BY id LIMIT 1",
            (instance_id,),
            conn,
        )
        if todo:
            status = _ROLE_STATUS.get(todo["role_ref"], customer["status"])
    if status and status != customer["status"]:
        db.execute(
            "UPDATE customer_application SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, customer["id"]),
            conn,
        )
    return status
