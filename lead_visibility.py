from datetime import datetime

from sqlalchemy import or_

from models import Lead, User, db


SPECIAL_PUBLIC_LEAD_USERNAMES = {'lucol', '玉婷'}
SPECIAL_PUBLIC_LEAD_CUTOFF = datetime(2026, 4, 1, 0, 0, 0)


def is_special_public_lead_user(user):
    username = (getattr(user, 'username', '') or '').strip().casefold()
    return username in SPECIAL_PUBLIC_LEAD_USERNAMES


def get_public_sales_user_ids_subquery():
    return db.session.query(User.id).filter(
        User.role.in_(['sales_manager', 'salesperson']),
        User.status.is_(True)
    ).subquery()


def special_public_lead_visibility_condition(user):
    return or_(
        Lead.created_at.is_(None),
        Lead.created_at < SPECIAL_PUBLIC_LEAD_CUTOFF,
        Lead.sales_user_id == user.id
    )


def apply_special_public_lead_visibility(query, user):
    if not is_special_public_lead_user(user):
        return query
    return query.filter(special_public_lead_visibility_condition(user))


def can_user_view_public_sales_lead(user, lead):
    if not (lead.sales_user and lead.sales_user.is_sales()):
        return False

    if not is_special_public_lead_user(user):
        return True

    return (
        lead.created_at is None
        or lead.created_at < SPECIAL_PUBLIC_LEAD_CUTOFF
        or lead.sales_user_id == user.id
    )
