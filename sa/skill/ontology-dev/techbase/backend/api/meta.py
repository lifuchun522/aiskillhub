from flask import Blueprint

from ontology.registry import get_dictionary_items
from utils.response import ok
from utils.security import login_required

bp = Blueprint("meta", __name__, url_prefix="/api/meta")

CUSTOMER_STATUS = ["草稿", "待客户经理审批", "待部门总经理审批", "已通过", "已驳回"]


@bp.get("/dictionaries")
@login_required
def dictionaries():
    return ok({
        "CUSTOMER_TYPE": get_dictionary_items("DICT-CUSTOMER-TYPE", "CUSTOMER_TYPE"),
        "CUSTOMER_LEVEL": get_dictionary_items("DICT-CUSTOMER-LEVEL", "CUSTOMER_LEVEL"),
    })


@bp.get("/customer-status")
@login_required
def customer_status():
    return ok(CUSTOMER_STATUS)


@bp.get("/rules")
@login_required
def rules():
    from ontology.registry import registry
    return ok([
        {
            "id": r["id"],
            "name": r.get("name", r["id"]),
            "description": r.get("description"),
            "expression": (r.get("expression") or "").strip(),
            "rule_type": r.get("ruleType"),
            "input_params": r.get("inputParams", []),
        }
        for r in registry["rules"].values()
    ])
