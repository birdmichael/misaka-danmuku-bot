import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from utils.api import call_danmaku_api
from utils.permission import check_admin_permission
from config import ConfigManager

logger = logging.getLogger(__name__)

@check_admin_permission
async def check_quota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查询并显示全局配额信息"""
    try:
        config = ConfigManager()
        response = call_danmaku_api(
            'GET',
            '/rate-limit/status',
            params={'token': config.danmaku_api.api_key}
        )
        if not response or not response.get('success'):
            error_msg = response.get('error') or response.get('message', '未知错误') if response else '未知错误'
            await update.message.reply_text(f"❌ 获取配额信息失败: {error_msg}")
            return

        data = response.get('data', {}) or {}
        if isinstance(data, dict):
            global_limit = data.get('globalLimit')
            request_count = data.get('globalRequestCount', 0)
            if isinstance(global_limit, (int, float)):
                total = global_limit
                remaining = max(global_limit - request_count, 0)
            elif str(global_limit).lower() in ['∞', 'inf', 'infinite', 'infinity'] or global_limit is None:
                total = remaining = '∞'
            else:
                total = remaining = None
        else:
            total = remaining = None

        if total is None and remaining is None:
            await update.message.reply_text("❌ API未返回配额信息")
            return

        total_display = total if total is not None else '未知'
        remaining_display = remaining if remaining is not None else '未知'
        await update.message.reply_text(
            f"📊 全局配额信息：\n剩余：{remaining_display}\n总配额：{total_display}"
        )
    except Exception as e:
        logger.error(f"查询配额信息失败: {e}")
        await update.message.reply_text("❌ 查询配额信息时发生错误")

def create_quota_handler():
    """创建查询配额命令处理器"""
    return CommandHandler('quota', check_quota)
