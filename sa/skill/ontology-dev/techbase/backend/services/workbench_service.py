import db
from engine.flow_engine import FlowEngine
from services import auth_service, customer_service


def _user_role_codes(user_id):
    return [r["code"] for r in auth_service.get_user_roles(user_id)]


def _role_in_clause(role_codes):
    if not role_codes:
        return "NULL"
    return ",".join("?" for _ in role_codes)


def _is_admin_id(user_id):
    return "*" in auth_service.get_permission_codes(user_id)


def todo(user_id, page=1, size=10):
    if _is_admin_id(user_id):
        where = "t.status='TODO'"
        params = []
    else:
        role_codes = _user_role_codes(user_id)
        where = f"t.status='TODO' AND (t.assignee_id=? OR t.role_ref IN ({_role_in_clause(role_codes)}))"
        params = [user_id] + role_codes
    total = db.query_one(f"SELECT COUNT(*) AS c FROM flow_task t WHERE {where}", params)["c"]
    rows = db.query(
        f"""
        SELECT t.*, i.business_key, i.creator_id, i.started_at,
               c.customer_name, c.customer_no, c.applicant_name
        FROM flow_task t
        JOIN flow_instance i ON i.id = t.instance_id
        LEFT JOIN customer_application c ON c.instance_id = i.id
        WHERE {where}
        ORDER BY t.created_at DESC LIMIT ? OFFSET ?
        """,
        params + [size, (page - 1) * size],
    )
    return {"list": rows, "total": total, "page": page, "size": size}


def done(user_id, page=1, size=10):
    if _is_admin_id(user_id):
        where = "t.status IN ('DONE','CANCEL')"
        params = []
    else:
        role_codes = _user_role_codes(user_id)
        where = f"t.status IN ('DONE','CANCEL') AND (t.assignee_id=? OR t.role_ref IN ({_role_in_clause(role_codes)}))"
        params = [user_id] + role_codes
    total = db.query_one(f"SELECT COUNT(*) AS c FROM flow_task t WHERE {where}", params)["c"]
    rows = db.query(
        f"""
        SELECT t.*, i.business_key, c.customer_name, c.customer_no
        FROM flow_task t
        JOIN flow_instance i ON i.id = t.instance_id
        LEFT JOIN customer_application c ON c.instance_id = i.id
        WHERE {where}
        ORDER BY t.done_at DESC LIMIT ? OFFSET ?
        """,
        params + [size, (page - 1) * size],
    )
    return {"list": rows, "total": total, "page": page, "size": size}


def requested(user_id, page=1, size=10):
    total = db.query_one(
        "SELECT COUNT(*) AS c FROM customer_application WHERE applicant_id=?",
        (user_id,),
    )["c"]
    rows = db.query(
        """
        SELECT c.*, i.status AS flow_status
        FROM customer_application c
        LEFT JOIN flow_instance i ON i.id = c.instance_id
        WHERE c.applicant_id=?
        ORDER BY c.id DESC LIMIT ? OFFSET ?
        """,
        (user_id, size, (page - 1) * size),
    )
    return {"list": rows, "total": total, "page": page, "size": size}


def _load_task_and_check(task_id, user):
    task = db.query_one("SELECT * FROM flow_task WHERE id = ?", (task_id,))
    if not task:
        raise ValueError("任务不存在")
    if task["status"] != "TODO":
        raise ValueError("任务已处理，不能重复操作")
    if is_admin(user):
        return task
    if task["assignee_id"] == user["id"]:
        return task
    role_codes = _user_role_codes(user["id"])
    if task["role_ref"] and task["role_ref"] in role_codes:
        return task
    raise ValueError("该任务不属于当前用户")


def is_admin(user):
    if not user:
        return False
    codes = auth_service.get_permission_codes(user["id"])
    return "*" in codes


def approve(task_id, comment, user):
    def _do(conn):
        task = _load_task_and_check(task_id, user)
        engine = FlowEngine(conn)
        engine.approve(task_id, comment, user["id"], user["real_name"])
        customer_service.sync_status_from_instance(task["instance_id"], conn)
        return task["instance_id"]

    db.transaction(_do)
    return True


def reject(task_id, comment, user):
    def _do(conn):
        task = _load_task_and_check(task_id, user)
        engine = FlowEngine(conn)
        engine.reject(task_id, comment, user["id"], user["real_name"])
        customer_service.sync_status_from_instance(task["instance_id"], conn)
        return task["instance_id"]

    db.transaction(_do)
    return True


def return_task(task_id, target_activity_id, comment, user):
    def _do(conn):
        task = _load_task_and_check(task_id, user)
        if not target_activity_id:
            target_activity_id = _first_approval_node(conn, task["instance_id"])
        engine = FlowEngine(conn)
        engine.return_to(task_id, target_activity_id, comment, user["id"], user["real_name"])
        customer_service.sync_status_from_instance(task["instance_id"], conn)

    db.transaction(_do)
    return True


def _first_approval_node(conn, instance_id):
    inst = db.query_one("SELECT * FROM flow_instance WHERE id = ?", (instance_id,), conn)
    definition = db.query_one("SELECT * FROM flow_definition WHERE id = ?", (inst["def_id"],), conn)
    import json
    graph = json.loads(definition["node_graph"] or "{}")
    start = next((n for n in graph["nodes"] if n["type"] == "start"), None)
    if not start:
        return None
    out = [e["target"] for e in graph["edges"] if e["source"] == start["id"]]
    return out[0] if out else None
