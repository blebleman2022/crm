#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沟通记录管理工具函数
"""

from models import db, CommunicationRecord, Lead, Customer
from datetime import datetime
from typing import List, Optional

class CommunicationManager:
    """沟通记录管理器"""
    
    @staticmethod
    def add_lead_communication(lead_id: int, content: str, created_at: Optional[datetime] = None) -> CommunicationRecord:
        """添加线索阶段的沟通记录"""
        record = CommunicationRecord(
            lead_id=lead_id,
            customer_id=None,
            content=content.strip(),
            created_at=created_at or datetime.utcnow()
        )
        db.session.add(record)
        db.session.commit()
        return record
    
    @staticmethod
    def add_customer_communication(lead_id: int, customer_id: int, content: str, created_at: Optional[datetime] = None) -> CommunicationRecord:
        """添加客户阶段的沟通记录"""
        record = CommunicationRecord(
            lead_id=lead_id,
            customer_id=customer_id,
            content=content.strip(),
            created_at=created_at or datetime.utcnow()
        )
        db.session.add(record)
        db.session.commit()
        return record
    
    @staticmethod
    def get_all_communications_by_lead(lead_id: int) -> List[CommunicationRecord]:
        """获取某个线索的所有沟通记录（包含客户阶段），按时间倒序排列"""
        return CommunicationRecord.query.filter_by(lead_id=lead_id)\
            .order_by(CommunicationRecord.created_at.desc()).all()
    
    @staticmethod
    def get_lead_communications(lead_id: int) -> List[CommunicationRecord]:
        """获取线索阶段的沟通记录"""
        return CommunicationRecord.query.filter_by(
            lead_id=lead_id,
            customer_id=None
        ).order_by(CommunicationRecord.created_at).all()
    
    @staticmethod
    def get_customer_communications(customer_id: int) -> List[CommunicationRecord]:
        """获取客户阶段的沟通记录"""
        return CommunicationRecord.query.filter_by(
            customer_id=customer_id
        ).order_by(CommunicationRecord.created_at).all()
    
    @staticmethod
    def get_recent_communications(lead_id: int, limit: int = 10) -> List[CommunicationRecord]:
        """获取最近的沟通记录"""
        return CommunicationRecord.query.filter_by(lead_id=lead_id)\
            .order_by(CommunicationRecord.created_at.desc())\
            .limit(limit).all()
    
    @staticmethod
    def update_communication(record_id: int, content: str) -> Optional[CommunicationRecord]:
        """更新沟通记录内容"""
        record = CommunicationRecord.query.get(record_id)
        if record:
            record.content = content.strip()
            db.session.commit()
        return record
    
    @staticmethod
    def delete_communication(record_id: int) -> bool:
        """删除沟通记录"""
        record = CommunicationRecord.query.get(record_id)
        if record:
            db.session.delete(record)
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def get_communication_stats(lead_id: int) -> dict:
        """获取沟通记录统计信息"""
        all_records = CommunicationRecord.query.filter_by(lead_id=lead_id).all()
        lead_records = [r for r in all_records if r.customer_id is None]
        customer_records = [r for r in all_records if r.customer_id is not None]
        
        return {
            'total_count': len(all_records),
            'lead_stage_count': len(lead_records),
            'customer_stage_count': len(customer_records),
            'first_communication': all_records[0].created_at if all_records else None,
            'last_communication': all_records[-1].created_at if all_records else None
        }

# 便捷函数
def add_lead_note(lead_id: int, content: str) -> CommunicationRecord:
    """添加线索备注（便捷函数）"""
    return CommunicationManager.add_lead_communication(lead_id, content)

def add_customer_feedback(customer_id: int, content: str) -> CommunicationRecord:
    """添加客户反馈（便捷函数）"""
    customer = Customer.query.get(customer_id)
    if not customer:
        raise ValueError(f"Customer {customer_id} not found")
    
    return CommunicationManager.add_customer_communication(
        lead_id=customer.lead_id,
        customer_id=customer_id,
        content=content
    )

def get_full_communication_history(lead_id: int) -> List[dict]:
    """获取完整的沟通历史（格式化输出）"""
    records = CommunicationManager.get_all_communications_by_lead(lead_id)
    
    history = []
    for record in records:
        stage = "客户阶段" if record.customer_id else "线索阶段"
        history.append({
            'id': record.id,
            'stage': stage,
            'content': record.content,
            'created_at': record.created_at,
            'lead_id': record.lead_id,
            'customer_id': record.customer_id
        })
    
    return history

def migrate_lead_notes_to_communications():
    """将线索备注迁移到沟通记录（一次性迁移函数）"""
    migrated_count = 0
    
    leads_with_notes = Lead.query.filter(Lead.follow_up_notes.isnot(None)).all()
    
    for lead in leads_with_notes:
        if lead.follow_up_notes and lead.follow_up_notes.strip():
            # 检查是否已经迁移
            existing = CommunicationRecord.query.filter_by(
                lead_id=lead.id,
                content=lead.follow_up_notes.strip()
            ).first()
            
            if not existing:
                CommunicationManager.add_lead_communication(
                    lead_id=lead.id,
                    content=lead.follow_up_notes.strip(),
                    created_at=lead.created_at
                )
                migrated_count += 1
    
    return migrated_count

# 查询辅助函数
def search_communications(keyword: str, lead_id: Optional[int] = None) -> List[CommunicationRecord]:
    """搜索沟通记录"""
    query = CommunicationRecord.query.filter(
        CommunicationRecord.content.contains(keyword)
    )
    
    if lead_id:
        query = query.filter_by(lead_id=lead_id)
    
    return query.order_by(CommunicationRecord.created_at.desc()).all()

def get_communications_by_date_range(lead_id: int, start_date: datetime, end_date: datetime) -> List[CommunicationRecord]:
    """按日期范围获取沟通记录"""
    return CommunicationRecord.query.filter(
        CommunicationRecord.lead_id == lead_id,
        CommunicationRecord.created_at >= start_date,
        CommunicationRecord.created_at <= end_date
    ).order_by(CommunicationRecord.created_at).all()
