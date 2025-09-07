from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from utils.permission import check_user_permission, is_admin

@check_user_permission
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """发送欢迎消息和指令列表"""
    user_id = update.effective_user.id
    is_user_admin = is_admin(user_id)
    
    if is_user_admin:
        welcome_msg = """
👋 欢迎使用 Misaka 弹幕系统机器人！
您是管理员，可使用以下所有指令：

【📥 媒体导入】
/search [关键词] - 搜索媒体（如：/search 火影忍者）
/auto - 自动导入媒体（支持关键词搜索和多平台链接导入）
/url - 为已存在的数据源导入指定集数
/refresh - 刷新数据源

【🔑 Token管理】
/tokens - 管理API访问令牌

【📊 配额查询】
/quota - 查询全局配额

【👥 用户管理】
/addUser <用户ID> - 添加用户
/deleteUser <用户ID> - 删除用户
/listUser - 查看用户列表

【其他】
/help  - 查看帮助信息
/cancel - 取消当前操作

💡 提示：直接输入命令或使用菜单选择功能！
        """
        
        # 管理员键盘，包含所有功能
        keyboard = [
            [KeyboardButton("/search"), KeyboardButton("/auto")],
            [KeyboardButton("/url"), KeyboardButton("/refresh")],
            [KeyboardButton("/tokens"), KeyboardButton("/quota")],
            [KeyboardButton("/help"), KeyboardButton("/cancel")]
        ]
    else:
        welcome_msg = """
👋 欢迎使用 Misaka 弹幕系统机器人！
您可以使用以下指令：

【📥 媒体搜索】
/search [关键词] - 搜索媒体（如：/search 火影忍者）
/auto - 自动导入媒体（支持关键词搜索和多平台链接导入）

【📊 配额查询】
/quota - 查询全局配额

【🔒 管理员功能】（需要管理员权限）
/url - 为已存在的数据源导入指定集数
/refresh - 刷新数据源
/tokens - 管理API访问令牌
/addUser <用户ID> - 添加用户
/deleteUser <用户ID> - 删除用户
/listUser - 查看用户列表

【其他】
/help  - 查看帮助信息
/cancel - 取消当前操作

💡 提示：直接输入命令或使用菜单选择功能！管理员功能需要相应权限。
        """
        
        # 普通用户键盘，显示所有功能但会有权限检查
        keyboard = [
            [KeyboardButton("/search"), KeyboardButton("/auto")],
            [KeyboardButton("/url"), KeyboardButton("/refresh")],
            [KeyboardButton("/tokens"), KeyboardButton("/quota")],
            [KeyboardButton("/help"), KeyboardButton("/cancel")]
        ]
    
    # 移除自定义键盘，只保留命令菜单
    await update.message.reply_text(welcome_msg, reply_markup=ReplyKeyboardRemove())

@check_user_permission
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示帮助信息"""
    user_id = update.effective_user.id
    is_user_admin = is_admin(user_id)
    
    if is_user_admin:
        help_text = """
🤖 Misaka 弹幕系统机器人 - 管理员帮助文档

【📥 媒体导入功能】
• /search [关键词] - 搜索并导入媒体
  示例：/search 火影忍者
  
• /auto - 自动导入媒体
  支持关键词搜索和多平台链接导入
  
• /url - 为已存在的数据源导入指定集数
  适用于已有数据源但需要补充集数的情况
  
• /refresh - 刷新数据源
  更新现有数据源信息

【🔑 Token管理】
• /tokens - 管理API访问令牌
  查看、创建、删除访问令牌

【📊 配额查询】
• /quota - 查询剩余全局配额和总配额

【👥 用户管理】
• /addUser <用户ID> - 添加用户
• /deleteUser <用户ID> - 删除用户
• /listUser - 查看用户列表

【📋 其他指令】
• /help - 显示此帮助信息
• /cancel - 取消当前操作
• /start - 返回主菜单

💡 使用提示：
- 所有操作都有引导界面，按提示操作即可
- 可以随时使用 /cancel 取消当前操作
- 遇到问题可以重新发送 /start 重置状态
        """
    else:
         help_text = """
🤖 Misaka 弹幕系统机器人 - 用户帮助文档

【📥 媒体搜索功能】
• /search [关键词] - 搜索媒体
  示例：/search 火影忍者

• /auto - 自动导入媒体
  支持关键词搜索和多平台链接导入

【📊 配额查询】
• /quota - 查询全局配额

【🔒 管理员功能】（需要管理员权限）
• /url - 为已存在的数据源导入指定集数
  适用于已有数据源但需要补充集数的情况

• /refresh - 刷新数据源
  更新现有数据源信息

• /tokens - 管理API访问令牌
  查看、创建、删除访问令牌

• /addUser <用户ID> - 添加用户
• /deleteUser <用户ID> - 删除用户
• /listUser - 查看用户列表

【📋 其他指令】
• /help - 显示此帮助信息
• /cancel - 取消当前操作
• /start - 返回主菜单

💡 使用提示：
- 所有操作都有引导界面，按提示操作即可
- 可以随时使用 /cancel 取消当前操作
- 管理员功能需要相应权限，非管理员点击会提示权限不足
- 遇到问题可以重新发送 /start 重置状态
         """
    
    await update.message.reply_text(help_text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """取消当前对话流程"""
    context.user_data.clear()
    await update.message.reply_text("✅ 已取消当前操作", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END
