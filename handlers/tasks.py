import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from utils.api import call_danmaku_api
from utils.permission import check_user_permission

logger = logging.getLogger(__name__)

@check_user_permission
async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查询任务列表，可按状态码过滤 (0=all,1=in_progress,2=completed)"""
    # 解析状态参数，默认 0（全部）
    status = "0"
    if context.args:
        arg = context.args[0].lower()
        status_map = {
            "0": "0",
            "1": "1",
            "2": "2",
            "all": "0",
            "in_progress": "1",
            "completed": "2",
        }
        if arg in status_map:
            status = status_map[arg]
    try:
        response = call_danmaku_api("GET", "/tasks", params={"status": status})
        if not response or not response.get("success"):
            error_msg = response.get("error") or response.get("message", "未知错误") if response else "未知错误"
            await update.message.reply_text(f"❌ 获取任务列表失败: {error_msg}")
            return
        tasks = response.get("data", [])
        if not tasks:
            await update.message.reply_text("📋 当前没有任务")
            return
        status_map = {
            "in_progress": "🟡 进行中",
            "completed": "✅ 已完成",
            "failed": "🔴 失败"
        }
        message_lines = ["📋 **任务列表**\n"]
        for item in tasks:
            task_id = item.get("taskId", "N/A")
            title = item.get("title", "N/A")
            task_status = status_map.get(item.get("status", ""), item.get("status", "未知"))
            progress = item.get("progress", 0)
            description = item.get("description", "")
            created_at = item.get("createdAt", "N/A")
            line = (
                f"• **{title}** (ID: `{task_id}`)\n"
                f"  状态: {task_status} | 进度: {progress}%\n"
                f"  描述: {description}\n"
                f"  创建时间: {created_at}\n"
            )
            message_lines.append(line)
        await update.message.reply_text("\n".join(message_lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"查询任务列表失败: {e}")
        await update.message.reply_text("❌ 查询任务列表时发生错误")

def create_tasks_handler():
    """创建任务查询命令处理器"""
    return CommandHandler('tasks', list_tasks)
