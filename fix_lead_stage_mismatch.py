#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量修正线索阶段（Lead.stage）与当前业务规则不一致的问题。

规则与 routes/leads.py::auto_update_lead_stage 保持一致：
1) 合同金额 > 0 且累计付款 >= 合同金额 -> 全款支付
2) 付款笔数 >= 2 -> 次笔支付
3) 付款笔数 >= 1 -> 首笔支付
4) 有见面时间 -> 线下见面
5) 否则 -> 获取联系方式

使用方式：
1) 仅预览差异（不落库）
   python3 fix_lead_stage_mismatch.py
2) 执行修复并提交
   python3 fix_lead_stage_mismatch.py --apply
"""

import argparse
from decimal import Decimal
from datetime import datetime

from sqlalchemy import func

from models import db, Lead, Payment
from run import app


def expected_stage(lead, payment_count, total_paid):
    """按当前规则计算期望阶段。"""
    contract_amount = lead.contract_amount or Decimal("0")
    if contract_amount > 0 and total_paid >= contract_amount:
        return Lead.STAGE_FULL_PAYMENT
    if payment_count >= 2:
        return Lead.STAGE_SECOND_PAYMENT
    if payment_count >= 1:
        return Lead.STAGE_FIRST_PAYMENT
    if lead.meeting_at:
        return Lead.STAGE_MEETING
    return Lead.STAGE_CONTACT


def main(apply_changes=False):
    with app.app_context():
        payment_stats_rows = (
            db.session.query(
                Payment.lead_id.label("lead_id"),
                func.count(Payment.id).label("payment_count"),
                func.coalesce(func.sum(Payment.amount), 0).label("total_paid"),
            )
            .group_by(Payment.lead_id)
            .all()
        )

        payment_stats = {
            row.lead_id: {
                "payment_count": int(row.payment_count or 0),
                "total_paid": row.total_paid or Decimal("0"),
            }
            for row in payment_stats_rows
        }

        leads = Lead.query.all()
        mismatches = []

        for lead in leads:
            stats = payment_stats.get(lead.id, None)
            payment_count = stats["payment_count"] if stats else 0
            total_paid = stats["total_paid"] if stats else Decimal("0")

            new_stage = expected_stage(lead, payment_count, total_paid)
            old_stage = lead.stage or ""
            if old_stage != new_stage:
                mismatches.append((lead, old_stage, new_stage, payment_count, total_paid))

        print("=" * 80)
        print("Lead 阶段一致性检查")
        print("=" * 80)
        print(f"总线索数: {len(leads)}")
        print(f"阶段不一致数: {len(mismatches)}")

        preview_count = min(len(mismatches), 20)
        if preview_count:
            print("\n示例（最多显示20条）：")
            for lead, old_stage, new_stage, payment_count, total_paid in mismatches[:preview_count]:
                print(
                    f"- Lead#{lead.id} {lead.get_display_name() or '-'} | "
                    f"旧阶段: {old_stage or '-'} -> 新阶段: {new_stage} | "
                    f"付款笔数: {payment_count} | 已付: {total_paid} | 合同: {lead.contract_amount}"
                )

        if not apply_changes:
            print("\n仅预览模式，未写入数据库。")
            print("如需执行修复，请加 --apply 参数。")
            return

        if not mismatches:
            print("\n无需修复，已全部一致。")
            return

        for lead, _old_stage, new_stage, _payment_count, _total_paid in mismatches:
            lead.stage = new_stage
            lead.updated_at = datetime.utcnow()

        db.session.commit()
        print(f"\n修复完成，已更新 {len(mismatches)} 条线索阶段。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="修复 Lead.stage 历史错误")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="执行修复并写入数据库（默认仅预览）",
    )
    args = parser.parse_args()
    main(apply_changes=args.apply)
