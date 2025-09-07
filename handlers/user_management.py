import os
import logging
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from utils.permission import check_admin_permission
from config import config
from dotenv import set_key, find_dotenv

logger = logging.getLogger(__name__)


def _save_user_ids():
    """Persist user ID lists to environment and .env file."""
    env_path = find_dotenv()
    if not env_path:
        env_path = '.env'
    env_path = Path(env_path)
    allowed_str = ",".join(str(uid) for uid in config.telegram.allowed_user_ids)
    admin_str = ",".join(str(uid) for uid in config.telegram.admin_user_ids)
    set_key(str(env_path), "ALLOWED_USER_IDS", allowed_str)
    set_key(str(env_path), "ADMIN_USER_IDS", admin_str)
    os.environ["ALLOWED_USER_IDS"] = allowed_str
    os.environ["ADMIN_USER_IDS"] = admin_str


@check_admin_permission
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("用法: /addUser <用户ID>")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("用户ID必须为数字")
        return
    if user_id in config.telegram.allowed_user_ids:
        await update.message.reply_text("用户已存在")
        return
    config.telegram.allowed_user_ids.append(user_id)
    _save_user_ids()
    await update.message.reply_text(f"✅ 已添加用户 {user_id}")


@check_admin_permission
async def delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("用法: /deleteUser <用户ID>")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("用户ID必须为数字")
        return
    if user_id not in config.telegram.allowed_user_ids:
        await update.message.reply_text("用户不存在")
        return
    config.telegram.allowed_user_ids = [uid for uid in config.telegram.allowed_user_ids if uid != user_id]
    if user_id in config.telegram.admin_user_ids:
        config.telegram.admin_user_ids = [uid for uid in config.telegram.admin_user_ids if uid != user_id]
    _save_user_ids()
    await update.message.reply_text(f"✅ 已删除用户 {user_id}")


@check_admin_permission
async def list_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    allowed = ", ".join(str(uid) for uid in config.telegram.allowed_user_ids) or "无"
    admins = ", ".join(str(uid) for uid in config.telegram.admin_user_ids) or "无"
    message = f"📋 允许用户: {allowed}\n👮 管理员: {admins}"
    await update.message.reply_text(message)


def create_user_management_handlers():
    return [
        ("add_user_handler", CommandHandler(["addUser", "adduser"], add_user)),
        ("delete_user_handler", CommandHandler(["deleteUser", "deleteuser"], delete_user)),
        ("list_user_handler", CommandHandler(["listUser", "listuser"], list_user)),
    ]
