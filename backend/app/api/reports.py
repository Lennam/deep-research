from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.utils.db import get_all_reports_meta, get_report_by_id, delete_report_by_id

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("")
async def list_reports():
    """获取历史报告列表的元数据（包含报告基本属性和事实数、源数量，但不返回大字段）"""
    try:
        reports = await get_all_reports_meta()
        return reports
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch reports list: {str(e)}")

@router.get("/{report_id}")
async def get_report(report_id: str):
    """获取单篇研究报告的完整详细信息，包含大模型 I/O 调试日志及工具追踪审计"""
    try:
        report = await get_report_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return report
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch report detail: {str(e)}")

@router.delete("/{report_id}")
async def delete_report(report_id: str):
    """从数据库中物理删除指定的报告记录"""
    try:
        deleted = await delete_report_by_id(report_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Report not found")
        return {
            "status": "success",
            "message": "报告已从数据库中物理删除"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete report: {str(e)}")
