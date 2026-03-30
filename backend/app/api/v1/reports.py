"""
报告相关的 API 路由
支持：异步生成、列表查询、详情、删除、下载
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import LLMReport, DetectionRecord, DetectionResult, TrackingRecord, AnimalType
from app.services.llm_service import llm_service
from app.services.task_manager import task_manager

router = APIRouter()
REPORT_DIR = Path("uploads/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)


class GenerateReportRequest(BaseModel):
    detection_record_id: int
    report_type: Optional[str] = None  # 自动从记录推断


def _build_context(record: DetectionRecord, db: Session) -> dict:
    """构建 LLM 报告所需上下文"""
    animal_type = "未知"
    if record.animal_type_id:
        at = db.query(AnimalType).filter(AnimalType.id == record.animal_type_id).first()
        if at:
            animal_type = at.name

    # 检测结果详情
    results = db.query(DetectionResult).filter(
        DetectionResult.detection_record_id == record.id
    ).all()
    detections_detail = "\n".join([
        f"- 目标{r.target_index+1}：{r.class_name}，置信度 {r.confidence:.1%}，状态："
        + ("正常" if r.health_status == "normal" else ("可疑" if r.health_status == "suspicious" else "异常"))
        for r in results
    ]) or "无详细检测数据"

    # 跟踪数据（视频）
    tracks = db.query(TrackingRecord).filter(
        TrackingRecord.detection_record_id == record.id
    ).all()
    tracks_detail = "\n".join([
        f"- 轨迹ID {t.track_id}：出现 {t.total_frames} 帧，平均置信度 {(t.avg_confidence or 0):.1%}，"
        + ("正常" if t.health_status_summary == "normal" else ("可疑" if t.health_status_summary == "suspicious" else "异常"))
        for t in tracks
    ]) or "无跟踪数据"

    return {
        "animal_type": animal_type,
        "created_at": str(record.created_at),
        "model_name": "检测模型",
        "total_targets": record.total_targets or 0,
        "normal_count": record.normal_count or 0,
        "suspicious_count": record.suspicious_count or 0,
        "abnormal_count": record.abnormal_count or 0,
        "detections_detail": detections_detail,
        "tracks_detail": tracks_detail,
        "total_frames": 0,
    }


# ==================== 生成报告 ====================

@router.post("/generate")
async def generate_report(
    data: GenerateReportRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """异步生成 LLM 报告，立即返回 task_id"""
    record = db.query(DetectionRecord).filter(
        DetectionRecord.id == data.detection_record_id,
        DetectionRecord.user_id == current_user["user_id"]
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="检测记录不存在")

    report_type = data.report_type or record.detection_type

    # 创建报告记录（pending状态）
    report = LLMReport(
        detection_record_id=record.id,
        report_type=report_type,
        report_title=f"{record.detection_type}检测报告 - {str(record.created_at)[:10]}",
        report_content="生成中...",
        generation_status="pending",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    report_id = report.id

    task_id = f"report_{report_id}_{uuid.uuid4().hex[:8]}"
    task_manager.create_task(task_id, {"report_id": report_id})

    # 构建上下文（在主线程读 DB）
    context = _build_context(record, db)
    is_mock = not llm_service.is_configured(db)

    def run_generation():
        from app.core.database import SessionLocal
        session = SessionLocal()
        try:
            rpt = session.query(LLMReport).filter(LLMReport.id == report_id).first()
            if rpt:
                rpt.generation_status = "generating"
                session.commit()

            content = llm_service.generate_report(report_type, context, session)

            # 保存报告文件
            fname = f"report_{report_id}.md"
            fpath = REPORT_DIR / fname
            fpath.write_text(content, encoding="utf-8")

            rpt = session.query(LLMReport).filter(LLMReport.id == report_id).first()
            if rpt:
                rpt.report_content = content
                rpt.report_file_path = str(fpath)
                rpt.generation_status = "completed"
                rpt.llm_model_used = "mock" if is_mock else "llm"
                # 提取摘要（取前200字）
                lines = [l for l in content.split("\n") if l.strip() and not l.startswith("#")]
                rpt.summary = (lines[0][:200] if lines else "")[:200]
                # 健康评估
                if context.get("abnormal_count", 0) == 0:
                    rpt.health_assessment = "正常"
                elif context.get("abnormal_count", 0) <= context.get("total_targets", 1) * 0.2:
                    rpt.health_assessment = "需关注"
                else:
                    rpt.health_assessment = "警告"
                session.commit()

            return {"report_id": report_id, "is_mock": is_mock}
        except Exception as e:
            rpt = session.query(LLMReport).filter(LLMReport.id == report_id).first()
            if rpt:
                rpt.generation_status = "failed"
                rpt.error_message = str(e)
                session.commit()
            raise
        finally:
            session.close()

    task_manager.run_in_background(task_id, run_generation)
    return {
        "message": "报告生成任务已提交",
        "task_id": task_id,
        "report_id": report_id,
        "is_mock": is_mock,
    }


@router.get("/task/{task_id}")
async def get_report_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    """查询报告生成任务状态"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {
        "task_id": task_id,
        "status": task["status"],
        "result": task.get("result"),
        "error": task.get("error"),
    }


# ==================== 报告列表 ====================

@router.get("/")
async def list_reports(
    page: int = 1,
    page_size: int = 10,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取报告列表（当前用户）"""
    # 通过 detection_record 关联用户
    query = db.query(LLMReport).join(
        DetectionRecord, DetectionRecord.id == LLMReport.detection_record_id
    ).filter(DetectionRecord.user_id == current_user["user_id"])

    total = query.count()
    reports = query.order_by(LLMReport.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return {
        "total": total,
        "reports": [
            {
                "id": r.id,
                "detection_record_id": r.detection_record_id,
                "report_type": r.report_type,
                "report_title": r.report_title,
                "generation_status": r.generation_status,
                "health_assessment": r.health_assessment,
                "summary": r.summary,
                "llm_model_used": r.llm_model_used,
                "created_at": str(r.created_at),
                "has_file": bool(r.report_file_path),
            }
            for r in reports
        ]
    }


# ==================== 报告详情 ====================

@router.get("/{report_id}")
async def get_report(
    report_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取报告详情（含完整内容）"""
    report = db.query(LLMReport).join(
        DetectionRecord, DetectionRecord.id == LLMReport.detection_record_id
    ).filter(
        LLMReport.id == report_id,
        DetectionRecord.user_id == current_user["user_id"]
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    return {
        "id": report.id,
        "detection_record_id": report.detection_record_id,
        "report_type": report.report_type,
        "report_title": report.report_title,
        "report_content": report.report_content,
        "generation_status": report.generation_status,
        "health_assessment": report.health_assessment,
        "summary": report.summary,
        "llm_model_used": report.llm_model_used,
        "error_message": report.error_message,
        "created_at": str(report.created_at),
    }


# ==================== 删除报告 ====================

@router.delete("/{report_id}")
async def delete_report(
    report_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除报告"""
    report = db.query(LLMReport).join(
        DetectionRecord, DetectionRecord.id == LLMReport.detection_record_id
    ).filter(
        LLMReport.id == report_id,
        DetectionRecord.user_id == current_user["user_id"]
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    db.delete(report)
    db.commit()
    return {"message": "删除成功"}


# ==================== 下载报告 ====================

@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """下载报告 Markdown 文件"""
    report = db.query(LLMReport).join(
        DetectionRecord, DetectionRecord.id == LLMReport.detection_record_id
    ).filter(
        LLMReport.id == report_id,
        DetectionRecord.user_id == current_user["user_id"]
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    if not report.report_file_path:
        # 动态生成文件
        content = report.report_content or ""
        fname = f"report_{report_id}.md"
        fpath = REPORT_DIR / fname
        fpath.write_text(content, encoding="utf-8")
        report.report_file_path = str(fpath)
        db.commit()
    if not Path(report.report_file_path).exists():
        raise HTTPException(status_code=404, detail="报告文件不存在")
    return FileResponse(
        report.report_file_path,
        media_type="text/markdown",
        filename=f"report_{report_id}.md"
    )


@router.get("/{report_id}/download/pdf")
async def download_report_pdf(
    report_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """下载 PDF 格式报告"""
    from app.services.pdf_service import generate_pdf
    report = db.query(LLMReport).join(
        DetectionRecord, DetectionRecord.id == LLMReport.detection_record_id
    ).filter(
        LLMReport.id == report_id,
        DetectionRecord.user_id == current_user["user_id"]
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    if report.generation_status != "completed":
        raise HTTPException(status_code=400, detail="报告尚未生成完成")

    # 检查是否已有 PDF
    pdf_path = str(REPORT_DIR / f"report_{report_id}.pdf")
    if not Path(pdf_path).exists():
        pdf_path = generate_pdf(
            report_id,
            report.report_title or f"检测报告 #{report_id}",
            report.report_content or ""
        )
    if not pdf_path or not Path(pdf_path).exists():
        # PDF 生成失败，返回 HTML
        from app.services.pdf_service import _generate_html_report
        html_path = _generate_html_report(
            report_id,
            report.report_title or f"检测报告 #{report_id}",
            report.report_content or ""
        )
        return FileResponse(
            html_path, media_type="text/html",
            filename=f"report_{report_id}.html"
        )
    media_type = "application/pdf" if pdf_path.endswith(".pdf") else "text/html"
    ext = ".pdf" if pdf_path.endswith(".pdf") else ".html"
    return FileResponse(
        pdf_path, media_type=media_type,
        filename=f"report_{report_id}{ext}"
    )
