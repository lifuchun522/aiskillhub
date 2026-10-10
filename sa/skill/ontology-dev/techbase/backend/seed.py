import json

import db
from utils.security import hash_password


def ensure_seed(conn):
    if db.query_one("SELECT COUNT(*) AS c FROM sys_user", (), conn)["c"] > 0:
        _ensure_flow_definition(conn)
        return
    _seed_roles(conn)
    _seed_permissions(conn)
    _seed_resources(conn)
    _seed_users(conn)
    _seed_role_permissions(conn)
    _ensure_flow_definition(conn)


def _seed_roles(conn):
    roles = [
        ("admin", "系统管理员", "系统内置超级管理员"),
        ("SALES", "业务人员", "客户申请提交人"),
        ("CUSTOMER_MANAGER", "客户经理", "客户审批第一节点"),
        ("DEPT_GENERAL_MANAGER", "部门总经理", "客户审批第二节点"),
    ]
    for code, name, desc in roles:
        db.execute(
            "INSERT INTO sys_role (name, code, parent_id, description, status) VALUES (?, ?, 0, ?, 1)",
            (name, code, desc),
            conn,
        )


def _seed_permissions(conn):
    perms = [
        ("customer:save", "客户申请暂存", "BEHAVIOR", "Customer_SaveAsDraft"),
        ("customer:submit", "客户申请提交", "BEHAVIOR", "Customer_Submit"),
        ("customer:query", "客户查询", "BEHAVIOR", "Customer_QueryList"),
        ("customer:approve-manager", "客户经理审批", "BEHAVIOR", "Customer_ApproveManager"),
        ("customer:approve-gm", "部门总经理审批", "BEHAVIOR", "Customer_ApproveGM"),
        ("system:user:add", "用户新增", "BEHAVIOR", "User_Add"),
        ("system:user:edit", "用户编辑", "BEHAVIOR", "User_Edit"),
        ("system:user:delete", "用户删除", "BEHAVIOR", "User_Delete"),
        ("system:user:assign-role", "分配角色", "BEHAVIOR", "User_AssignRole"),
        ("system:user:reset-pwd", "重置密码", "BEHAVIOR", "User_ResetPassword"),
        ("system:role:add", "角色新增", "BEHAVIOR", "Role_Add"),
        ("system:role:edit", "角色编辑", "BEHAVIOR", "Role_Edit"),
        ("system:role:delete", "角色删除", "BEHAVIOR", "Role_Delete"),
        ("system:role:assign", "分配权限资源", "BEHAVIOR", "Role_Assign"),
        ("system:permission:add", "权限新增", "BEHAVIOR", "Permission_Add"),
        ("system:permission:edit", "权限编辑", "BEHAVIOR", "Permission_Edit"),
        ("system:permission:delete", "权限删除", "BEHAVIOR", "Permission_Delete"),
        ("system:resource:add", "资源新增", "BEHAVIOR", "Resource_Add"),
        ("system:resource:edit", "资源编辑", "BEHAVIOR", "Resource_Edit"),
        ("system:resource:delete", "资源删除", "BEHAVIOR", "Resource_Delete"),
        ("flow:definition:add", "流程新增", "BEHAVIOR", "Flow_Add"),
        ("flow:definition:edit", "流程编辑", "BEHAVIOR", "Flow_Edit"),
        ("flow:definition:publish", "流程发布", "BEHAVIOR", "Flow_Publish"),
        ("flow:instance:terminate", "强制终止", "BEHAVIOR", "Flow_Terminate"),
        ("flow:task:transfer", "任务转办", "BEHAVIOR", "Flow_Transfer"),
        ("flow:task:urge", "任务催办", "BEHAVIOR", "Flow_Urge"),
    ]
    for code, name, tt, ref in perms:
        db.execute(
            "INSERT INTO sys_permission (code, name, target_type, target_ref, data_scope, status) VALUES (?, ?, ?, ?, 'ALL', 1)",
            (code, name, tt, ref),
            conn,
        )


def _seed_resources(conn):
    resources = [
        # (parent_code, name, code, permission_code, type, path, icon, sort)
        (None, "客户管理", "menu-customer", None, "DIRECTORY", None, "Users", 10),
        ("menu-customer", "客户申请", "menu-customer-apply", "customer:save", "MENU", "/customer/apply", "UserPlus", 11),
        ("menu-customer", "客户查询", "menu-customer-query", "customer:query", "MENU", "/customer/query", "Search", 12),
        (None, "审批中心", "menu-workbench", None, "DIRECTORY", None, "ClipboardList", 20),
        ("menu-workbench", "我的待办", "menu-workbench-todo", None, "MENU", "/workbench/todo", "Inbox", 21),
        ("menu-workbench", "我的已办", "menu-workbench-done", None, "MENU", "/workbench/done", "CheckSquare", 22),
        ("menu-workbench", "我的申请", "menu-workbench-requested", None, "MENU", "/workbench/requested", "FileText", 23),
        (None, "流程管理", "menu-flow", None, "DIRECTORY", None, "GitBranch", 30),
        ("menu-flow", "流程定义", "menu-flow-definition", "flow:manage", "MENU", "/flow/definitions", "Workflow", 31),
        ("menu-flow", "流程实例", "menu-flow-instance", "flow:manage", "MENU", "/flow/instances", "List", 32),
        ("menu-flow", "任务管理", "menu-flow-task", "flow:manage", "MENU", "/flow/tasks", "ListChecks", 33),
        (None, "系统管理", "menu-system", None, "DIRECTORY", None, "Settings", 40),
        ("menu-system", "用户管理", "menu-system-user", "system:manage", "MENU", "/system/users", "User", 41),
        ("menu-system", "角色管理", "menu-system-role", "system:manage", "MENU", "/system/roles", "Shield", 42),
        ("menu-system", "权限管理", "menu-system-permission", "system:manage", "MENU", "/system/permissions", "Key", 43),
        ("menu-system", "资源管理", "menu-system-resource", "system:manage", "MENU", "/system/resources", "Menu", 44),
    ]
    id_map = {}
    for parent_code, name, code, pc, rtype, path, icon, sort in resources:
        parent_id = id_map.get(parent_code, 0) if parent_code else 0
        rid = db.execute(
            """
            INSERT INTO sys_resource (parent_id, name, code, permission_code, type, path, component, icon, sort_order, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (parent_id, name, code, pc, rtype, path, None, icon, sort),
            conn,
        )[0]
        id_map[code] = rid


def _seed_users(conn):
    users = [
        ("admin", "admin123", "管理员", "admin"),
        ("sales", "123456", "王业务", "SALES"),
        ("cmanager", "123456", "张经理", "CUSTOMER_MANAGER"),
        ("gm", "123456", "李总", "DEPT_GENERAL_MANAGER"),
    ]
    for username, pwd, real_name, role_code in users:
        uid = db.execute(
            "INSERT INTO sys_user (username, password, real_name, actor_type, status) VALUES (?, ?, ?, 'HUMAN', 1)",
            (username, hash_password(pwd), real_name),
            conn,
        )[0]
        role = db.query_one("SELECT id FROM sys_role WHERE code = ?", (role_code,), conn)
        db.execute("INSERT INTO sys_user_role (user_id, role_id) VALUES (?, ?)", (uid, role["id"]), conn)


def _seed_role_permissions(conn):
    mapping = {
        "SALES": ["customer:save", "customer:submit", "customer:query"],
        "CUSTOMER_MANAGER": ["customer:approve-manager", "customer:query"],
        "DEPT_GENERAL_MANAGER": ["customer:approve-gm", "customer:query"],
    }
    for role_code, perm_codes in mapping.items():
        role = db.query_one("SELECT id FROM sys_role WHERE code = ?", (role_code,), conn)
        for pc in perm_codes:
            perm = db.query_one("SELECT id FROM sys_permission WHERE code = ?", (pc,), conn)
            db.execute(
                "INSERT INTO sys_role_permission (role_id, permission_id) VALUES (?, ?)",
                (role["id"], perm["id"]),
                conn,
            )


def _ensure_flow_definition(conn):
    from ontology.registry import registry
    flows = registry.get("flows", {})
    for code, flow in flows.items():
        if db.query_one("SELECT id FROM flow_definition WHERE code = ?", (code,), conn):
            continue
        trigger = flow.get("trigger", {})
        db.execute(
            """
            INSERT INTO flow_definition (code, name, flow_type, trigger_type, trigger_behavior, description, node_graph, version, status, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, 1)
            """,
            (
                code, flow.get("name", code), flow.get("flowType", "APPROVAL"),
                trigger.get("triggerType", "MANUAL"), trigger.get("behaviorRef"),
                flow.get("description"), json.dumps(flow.get("nodeGraph", {}), ensure_ascii=False),
            ),
            conn,
        )
