"""
沟通记录管理工具类
统一管理线索和客户阶段的沟通记录
"""

from datetime import datetime
from models import db, CommunicationRecord, Lead, Customer


class CommunicationManager:
    """沟通记录管理器"""
    
    @staticmethod
    def add_lead_communication(lead_id, content, created_at=None):
        """
        添加线索阶段沟通记录
        
        Args:
            lead_id (int): 线索ID
            content (str): 沟通内容
            created_at (datetime): 创建时间，默认为当前时间
            
        Returns:
            CommunicationRecord: 创建的沟通记录
        """
        if not content or not content.strip():
            raise ValueError("沟通内容不能为空")
            
        # 验证线索是否存在
        lead = Lead.query.get(lead_id)
        if not lead:
            raise ValueError(f"线索ID {lead_id} 不存在")
            
        record = CommunicationRecord(
            lead_id=lead_id,
            customer_id=None,  # 线索阶段没有客户ID
            content=content.strip(),
            created_at=created_at or datetime.utcnow()
        )
        
        db.session.add(record)
        db.session.commit()
        
        return record
    
    @staticmethod
    def add_customer_communication(lead_id, customer_id, content, created_at=None):
        """
        添加客户阶段沟通记录
        
        Args:
            lead_id (int): 线索ID
            customer_id (int): 客户ID
            content (str): 沟通内容
            created_at (datetime): 创建时间，默认为当前时间
            
        Returns:
            CommunicationRecord: 创建的沟通记录
        """
        if not content or not content.strip():
            raise ValueError("沟通内容不能为空")
            
        # 验证线索和客户是否存在
        lead = Lead.query.get(lead_id)
        if not lead:
            raise ValueError(f"线索ID {lead_id} 不存在")
            
        customer = Customer.query.get(customer_id)
        if not customer:
            raise ValueError(f"客户ID {customer_id} 不存在")
            
        # 验证客户是否属于该线索
        if customer.lead_id != lead_id:
            raise ValueError(f"客户ID {customer_id} 不属于线索ID {lead_id}")
            
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
    def get_lead_communications(lead_id):
        """
        获取线索阶段的沟通记录
        
        Args:
            lead_id (int): 线索ID
            
        Returns:
            list: 沟通记录列表，按时间倒序
        """
        return CommunicationRecord.query.filter_by(
            lead_id=lead_id,
            customer_id=None
        ).order_by(CommunicationRecord.created_at.desc()).all()
    
    @staticmethod
    def get_customer_communications(customer_id):
        """
        获取客户阶段的沟通记录
        
        Args:
            customer_id (int): 客户ID
            
        Returns:
            list: 沟通记录列表，按时间倒序
        """
        return CommunicationRecord.query.filter_by(
            customer_id=customer_id
        ).order_by(CommunicationRecord.created_at.desc()).all()
    
    @staticmethod
    def get_all_communications_by_lead(lead_id):
        """
        获取某个线索的所有沟通记录（包括线索阶段和客户阶段）
        
        Args:
            lead_id (int): 线索ID
            
        Returns:
            list: 沟通记录列表，按时间倒序
        """
        return CommunicationRecord.query.filter_by(
            lead_id=lead_id
        ).order_by(CommunicationRecord.created_at.desc()).all()
    
    @staticmethod
    def get_communication_stats(lead_id):
        """
        获取沟通记录统计信息
        
        Args:
            lead_id (int): 线索ID
            
        Returns:
            dict: 统计信息
        """
        # 总记录数
        total_count = CommunicationRecord.query.filter_by(lead_id=lead_id).count()
        
        # 线索阶段记录数
        lead_count = CommunicationRecord.query.filter_by(
            lead_id=lead_id,
            customer_id=None
        ).count()
        
        # 客户阶段记录数
        customer_count = CommunicationRecord.query.filter(
            CommunicationRecord.lead_id == lead_id,
            CommunicationRecord.customer_id.isnot(None)
        ).count()
        
        # 最近一次沟通时间
        latest_record = CommunicationRecord.query.filter_by(
            lead_id=lead_id
        ).order_by(CommunicationRecord.created_at.desc()).first()
        
        latest_communication_time = None
        if latest_record:
            latest_communication_time = latest_record.created_at
        
        return {
            'total_count': total_count,
            'lead_stage_count': lead_count,
            'customer_stage_count': customer_count,
            'latest_communication_time': latest_communication_time
        }
    
    @staticmethod
    def delete_communication(record_id):
        """
        删除沟通记录
        
        Args:
            record_id (int): 记录ID
            
        Returns:
            bool: 是否删除成功
        """
        record = CommunicationRecord.query.get(record_id)
        if not record:
            return False
            
        db.session.delete(record)
        db.session.commit()
        
        return True
    
    @staticmethod
    def update_communication(record_id, content):
        """
        更新沟通记录内容
        
        Args:
            record_id (int): 记录ID
            content (str): 新的沟通内容
            
        Returns:
            CommunicationRecord: 更新后的记录，如果记录不存在返回None
        """
        if not content or not content.strip():
            raise ValueError("沟通内容不能为空")
            
        record = CommunicationRecord.query.get(record_id)
        if not record:
            return None
            
        record.content = content.strip()
        db.session.commit()
        
        return record
