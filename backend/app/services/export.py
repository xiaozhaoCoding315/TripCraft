"""
TripCraft Export Service

Provides itinerary export functionality in multiple formats:
- JSON: Machine-readable format
- Markdown: Human-readable text format
- Simple text: Plain text for sharing
"""

import json
from datetime import datetime, timezone
from typing import Any

from app.models.travel import TravelPlan


class ExportService:
    """Service for exporting travel plans in various formats"""

    @staticmethod
    def to_json(plan: TravelPlan, pretty: bool = True) -> str:
        """Export plan as JSON string"""
        data = plan.model_dump()
        data["exported_at"] = datetime.now(timezone.utc).isoformat()
        data["format"] = "json"

        if pretty:
            return json.dumps(data, ensure_ascii=False, indent=2)
        return json.dumps(data, ensure_ascii=False)

    @staticmethod
    def to_markdown(plan: TravelPlan) -> str:
        """Export plan as Markdown"""
        lines = []

        # Header
        lines.append(f"# 🌍 {plan.destination} 旅行计划")
        lines.append("")
        lines.append(f"**版本**: v{plan.version}")
        lines.append(f"**总天数**: {len(plan.days)} 天")
        lines.append(f"**预计费用**: ¥{plan.total_estimated_cost or 0:,.0f}")
        lines.append(f"**导出时间**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Daily itinerary
        for day in plan.days:
            lines.append(f"## 📅 第 {day.day} 天")
            if day.date:
                lines.append(f"**日期**: {day.date}")
            if day.weather_summary:
                lines.append(f"**天气**: {day.weather_summary}")
            lines.append("")

            # Timeline
            for item in day.items:
                time_emoji = {
                    "transport": "🚗",
                    "attraction": "🎯",
                    "meal": "🍜",
                    "hotel": "🏨",
                    "rest": "☕",
                    "note": "📝",
                }.get(item.type, "📍")

                lines.append(f"### {time_emoji} {item.time} - {item.title}")
                if item.description:
                    lines.append(f"")
                    lines.append(f"{item.description}")
                if item.location and item.location.address:
                    lines.append(f"")
                    lines.append(f"📍 地址: {item.location.address}")
                if item.cost and item.cost > 0:
                    lines.append(f"")
                    lines.append(f"💰 费用: ¥{item.cost}")
                if item.duration_minutes:
                    lines.append(f"")
                    lines.append(f"⏱️ 时长: {item.duration_minutes} 分钟")
                if item.source_refs:
                    sources = ", ".join(ref.label for ref in item.source_refs)
                    lines.append(f"")
                    lines.append(f"📚 来源: {sources}")
                lines.append("")

            # Day summary
            if day.estimated_cost:
                lines.append(f"**当日费用**: ¥{day.estimated_cost:,.0f}")
            lines.append("")
            lines.append("---")
            lines.append("")

        # Revision history
        if plan.revisions:
            lines.append("## 📝 修订历史")
            lines.append("")
            for revision in plan.revisions:
                status = "✅ 通过" if revision.passed else "⚠️ 需修改"
                lines.append(f"### v{revision.version} - {status}")
                lines.append(f"**摘要**: {revision.summary}")
                lines.append("")
                for comment in revision.comments:
                    severity_emoji = {
                        "critical": "🔴",
                        "warning": "🟡",
                        "info": "🔵",
                    }.get(comment.severity, "⚪")
                    lines.append(f"- {severity_emoji} **{comment.dimension}**: {comment.message}")
                    if comment.suggestion:
                        lines.append(f"  - 💡 建议: {comment.suggestion}")
                lines.append("")

        return "\n".join(lines)

    @staticmethod
    def to_plain_text(plan: TravelPlan) -> str:
        """Export plan as plain text"""
        lines = []

        lines.append(f"{'='*50}")
        lines.append(f"  {plan.destination} 旅行计划")
        lines.append(f"  版本: v{plan.version} | 天数: {len(plan.days)} 天")
        lines.append(f"  预计费用: ¥{plan.total_estimated_cost or 0:,.0f}")
        lines.append(f"{'='*50}")
        lines.append("")

        for day in plan.days:
            lines.append(f"--- 第 {day.day} 天 ---")
            if day.date:
                lines.append(f"日期: {day.date}")
            lines.append("")

            for item in day.items:
                lines.append(f"{item.time} | {item.title}")
                if item.description:
                    lines.append(f"  {item.description}")
                if item.location and item.location.address:
                    lines.append(f"  地址: {item.location.address}")
                if item.cost and item.cost > 0:
                    lines.append(f"  费用: ¥{item.cost}")
                lines.append("")

            if day.estimated_cost:
                lines.append(f"当日费用: ¥{day.estimated_cost:,.0f}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def get_export_filename(plan: TravelPlan, extension: str = "json") -> str:
        """Generate export filename"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        destination = plan.destination.replace(" ", "_")
        return f"tripcraft_{destination}_v{plan.version}_{timestamp}.{extension}"


export_service = ExportService()
