from flask import Blueprint, request

from services import auth_service, customer_service
from utils.response import fail, ok
from utils.security import login_required

bp = Blueprint("customer", __name__, url_prefix="/api/customer")


@bp.get("")
@login_required
def list_customers():
    page = int(request.args.get("page", 1))
    size = int(request.args.get("size", 10))
    filters = {
        "customer_no": request.args.get("customer_no"),
        "customer_name": request.args.get("customer_name"),
        "status": request.args.get("status"),
    }
    return ok(customer_service.list_customers(page, size, filters))


@bp.get("/<int:customer_id>")
@login_required
def get_customer(customer_id):
    return ok(customer_service.get_customer(customer_id))


@bp.post("/draft")
@login_required
def create_draft():
    data = request.get_json(silent=True) or {}
    try:
        customer = customer_service.create_draft(data, auth_service.current_user())
        return ok(customer, "暂存成功")
    except ValueError as e:
        return fail(str(e))


@bp.put("/<int:customer_id>/draft")
@login_required
def update_draft(customer_id):
    data = request.get_json(silent=True) or {}
    try:
        customer = customer_service.update_draft(customer_id, data, auth_service.current_user())
        return ok(customer, "暂存成功")
    except ValueError as e:
        return fail(str(e))


@bp.post("/<int:customer_id>/submit")
@login_required
def submit(customer_id):
    try:
        customer = customer_service.submit(customer_id, auth_service.current_user())
        return ok(customer, "提交成功，已启动客户审批流")
    except ValueError as e:
        return fail(str(e))


@bp.post("/<int:customer_id>/withdraw")
@login_required
def withdraw(customer_id):
    try:
        customer = customer_service.withdraw(customer_id, auth_service.current_user())
        return ok(customer, "已撤回")
    except ValueError as e:
        return fail(str(e))
