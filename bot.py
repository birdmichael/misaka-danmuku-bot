import logging
import asyncio
import importlib
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileModifiedEvent,
    FileCreatedEvent,
    FileDeletedEvent
)

# ------------------------------
# Telegram 相关模块导入
# ------------------------------
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    Application
)

# ------------------------------
# 轮询管理器导入
# ------------------------------


# ------------------------------
# 全局配置常量
# ------------------------------
# 热更新监听目录/文件（核心业务逻辑相关）
WATCHED_DIRS = [
    Path(__file__).parent / "handlers",  # 处理器目录
    Path(__file__).parent / "callback",  # 回调函数目录
    Path(__file__).parent / "utils",     # 工具函数目录
    Path(__file__).parent / "config.py"  # 配置文件（单独监听）
]
# 热更新排除文件（避免无关文件触发更新）
EXCLUDE_PATTERNS = [
    "__pycache__", ".pyc", ".pyo", ".pyd",  # 编译缓存文件
    ".log", ".swp", ".tmp"                  # 日志/临时文件
]
# 全局存储：当前已注册的处理器（类型注解用字符串"Handler"避免导入依赖）
current_handlers: Dict[str, "Handler"] = {}
# 对话状态常量（仅保留搜索媒体相关）
SEARCH_MEDIA = 0
SEARCH_RESULTS = 1

# ------------------------------
# 日志配置（支持 Docker 日志查看）
# ------------------------------
logger = logging.getLogger(__name__)
# 初始化日志配置（稍后会根据配置文件更新）
logging.basicConfig(
    level=logging.INFO, # 默认级别，稍后会根据配置文件更新
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

# 设置第三方库的日志级别为 WARNING，减少噪音
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('telegram.ext._updater').setLevel(logging.WARNING)
logging.getLogger('telegram.ext._application').setLevel(logging.WARNING)

# 过滤 PTB 的 ConversationHandler 警告（这些警告不影响功能）
import warnings
warnings.filterwarnings('ignore', message='.*per_message.*CallbackQueryHandler.*', category=UserWarning)

# ------------------------------
# 模块导入与重载核心函数
# ------------------------------
def _import_modules():
    """
    一个独立的函数，用于清除模块缓存并导入最新的模块。
    这个函数是热更新成功的关键。
    """
    # 需要清理的模块前缀列表
    module_prefixes = ['config', 'utils', 'handlers', 'callback']
    
    # 递归清理所有相关模块（包括子模块）
    modules_to_delete = []
    for module_name in list(sys.modules.keys()):
        for prefix in module_prefixes:
            if module_name == prefix or module_name.startswith(prefix + '.'):
                modules_to_delete.append(module_name)
                break
    
    # 删除模块缓存
    for module_name in modules_to_delete:
        logger.debug(f"🔄 Clearing module cache: {module_name}")
        del sys.modules[module_name]
    
    # 强制重新导入
    import config
    import handlers
    import callback
    
    # 创建配置管理器实例
    config_manager = config.ConfigManager()
    
    # 更新日志级别
    log_level = getattr(logging, config_manager.app.log_level.upper(), logging.INFO)
    logging.getLogger().setLevel(log_level)
    logger.setLevel(log_level)
    
    logger.info(f"✅ Cleared {len(modules_to_delete)} cached modules and re-imported")
    logger.info(f"📝 Log level set to: {config_manager.app.log_level.upper()}")
    return config_manager, handlers, callback

# ------------------------------
# 1. 热更新核心：文件变更监听与模块重载
# ------------------------------
class CodeChangeHandler(FileSystemEventHandler):
    """文件系统事件处理器：检测代码变更并触发处理器热更新"""
    def __init__(self, application: Application, loop: asyncio.AbstractEventLoop):
        self.application = application
        self.loop = loop
        self.last_reload_time = 0
        self.reload_cooldown = 1

    def is_excluded(self, path: str) -> bool:
        """判断文件是否属于排除列表"""
        return any(pattern in path for pattern in EXCLUDE_PATTERNS)

    def on_modified(self, event: FileModifiedEvent):
        """文件被修改时触发"""
        if not event.is_directory and not self.is_excluded(event.src_path):
            self.trigger_reload(f"File modified: {event.src_path}")

    def on_created(self, event: FileCreatedEvent):
        """文件被创建时触发"""
        if not event.is_directory and not self.is_excluded(event.src_path):
            self.trigger_reload(f"File created: {event.src_path}")

    def on_deleted(self, event: FileDeletedEvent):
        """文件被删除时触发"""
        if not event.is_directory and not self.is_excluded(event.src_path):
            self.trigger_reload(f"File deleted: {event.src_path}")

    def trigger_reload(self, reason: str):
        """触发热重载（带防抖动）"""
        import time
        current_time = time.time()
        if current_time - self.last_reload_time < self.reload_cooldown:
            logger.debug(f"🔄 Hot reload cooldown, ignoring change: {reason}")
            return

        self.last_reload_time = current_time
        logger.info(f"🔥 Code change detected, triggering hot reload: {reason}")
        
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.reload_modules_and_handlers(),
                loop=self.loop
            )
            # 不等待结果，让热更新异步执行
            logger.debug(f"🚀 Hot reload task scheduled successfully")
        except Exception as e:
            logger.error(f"❌ Failed to schedule hot reload: {str(e)}", exc_info=True)

    async def reload_modules_and_handlers(self):
        """重载核心模块 + 更新机器人处理器"""
        try:
            logger.info("🔄 Starting hot reload process...")
            
            # 步骤1: 使用我们新的导入函数，获取最新的模块引用
            logger.debug("📦 Step 1: Re-importing modules...")
            reloaded_config, reloaded_handlers, reloaded_callback = _import_modules()
            logger.info("✅ All core modules re-imported from scratch")

            # 步骤2: 移除旧处理器
            logger.debug("🗑️ Step 2: Removing old handlers...")
            await self.remove_old_handlers()
            logger.info("✅ Old handlers removed")

            # 步骤3: 注册新处理器（使用重新导入的最新模块）
            logger.debug("🔧 Step 3: Registering new handlers...")
            await self.register_new_handlers(reloaded_handlers, reloaded_callback)
            logger.info("🎉 Hot reload completed successfully! New logic is now active.")

        except Exception as e:
            logger.error(f"❌ Hot reload failed! Error: {str(e)}", exc_info=True)
            logger.error("🔧 Please check your code for syntax errors or import issues.")

    async def remove_old_handlers(self):
        """移除机器人中已注册的旧处理器"""
        if not current_handlers:
            logger.debug("ℹ️ No old handlers to remove")
            return

        for handler_name, handler in current_handlers.items():
            self.application.remove_handler(handler)
            logger.debug(f"ℹ️ Removed old handler: {handler_name}")
        
        current_handlers.clear()

    async def register_new_handlers(self, handlers_module, callback_module):
        """注册最新的处理器"""
        _setup_handlers(self.application, handlers_module, callback_module)

# ------------------------------
# 2. 机器人初始化（含初始处理器注册）
# ------------------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """全局错误处理器：记录所有未处理的异常"""
    logger.error(f"❌ Exception while handling an update: {context.error}", exc_info=context.error)
    
    # 如果有用户更新，尝试发送错误消息给用户
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ 抱歉，处理您的请求时发生了错误。请稍后重试或联系管理员。"
            )
        except Exception as e:
            logger.error(f"❌ Failed to send error message to user: {e}")

async def _setup_bot_commands(application: Application):
    """设置 Bot 命令菜单，让用户在 Telegram 客户端看到可用命令"""
    commands = [
        BotCommand("start", "开始使用机器人"),
        BotCommand("auto", "自动导入媒体（支持多平台链接）"),
        BotCommand("search", "搜索媒体内容"),
        BotCommand("url", "为已存在的数据源导入指定集数"),
        BotCommand("refresh", "刷新数据源"),
        BotCommand("tokens", "管理API令牌"),
        BotCommand("quota", "查看全局配额"),
        BotCommand("adduser", "添加用户"),
        BotCommand("deleteuser", "删除用户"),
        BotCommand("listuser", "列出用户"),
        BotCommand("help", "查看帮助信息"),
        BotCommand("cancel", "取消当前操作")
    ]
    
    try:
        await application.bot.set_my_commands(commands)
        logger.info(f"✅ Bot commands menu set successfully: {len(commands)} commands")
    except Exception as e:
        logger.error(f"❌ Failed to set bot commands: {e}")

def _wrap_with_session_management(handler_func):
    """包装处理器函数"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await handler_func(update, context)
    return wrapper

def _wrap_conversation_entry_point(handler_func):
    """包装对话入口点处理器"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await handler_func(update, context)
    return wrapper

def _setup_handlers(application, handlers_module, callback_module):
    """通用的处理器设置函数"""
    start = handlers_module.start
    help_command = handlers_module.help_command
    cancel = handlers_module.cancel
    search_media = handlers_module.search_media
    search_media_input = handlers_module.search_media_input
    import_auto = handlers_module.import_auto
    import_auto_keyword_input = handlers_module.import_auto_keyword_input
    import_auto_id_input = handlers_module.import_auto_id_input
    import_auto_season_selection = handlers_module.import_auto_season_selection
    # import_auto_season_input = handlers_module.import_auto_season_input  # 已移除
# import_auto_episode_input = handlers_module.import_auto_episode_input  # 已移除
    handle_import_callback = callback_module.handle_import_callback
    handle_get_episode_callback = callback_module.handle_get_episode_callback
    handle_episode_range_input = callback_module.handle_episode_range_input
    cancel_episode_input = callback_module.cancel_episode_input
    handle_import_auto_callback = callback_module.handle_import_auto_callback
    handle_search_type_callback = callback_module.handle_search_type_callback
    handle_media_type_callback = callback_module.handle_media_type_callback
    
    # 导入import_url处理器
    from handlers.import_url import create_import_url_handler
    


    # 创建import_auto回调处理器（需要在ConversationHandler之前定义）
    import_auto_callback_handler = CallbackQueryHandler(
        _wrap_with_session_management(handle_import_auto_callback),
        pattern=r'{"action": "import_auto_.*"}'
    )

    # 创建会话处理器
    search_handler = ConversationHandler(
        entry_points=[CommandHandler("search", _wrap_conversation_entry_point(search_media))],
        states={
            SEARCH_MEDIA: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, 
                    _wrap_with_session_management(search_media_input)
                )
            ],
            SEARCH_RESULTS: [
                # 在搜索结果状态下，用户可以点击按钮或取消
                # 按钮点击由独立的CallbackQueryHandler处理
                CommandHandler("cancel", _wrap_with_session_management(cancel))
            ],
        },
        fallbacks=[
            CommandHandler("cancel", _wrap_with_session_management(cancel)),
            CommandHandler("search", _wrap_conversation_entry_point(search_media)),
            CommandHandler("auto", _wrap_conversation_entry_point(import_auto)),
            CommandHandler("start", _wrap_with_session_management(start)),
            CommandHandler("help", _wrap_with_session_management(help_command))
        ],
    )
    application.add_handler(search_handler)
    current_handlers["search_handler"] = search_handler

    # 创建集数输入会话处理器
    episode_input_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            _wrap_conversation_entry_point(handle_get_episode_callback),
            pattern=r'{"(action|a)": "(start_input_range|get_episodes|get_media_episode|switch_episode_page)".*}'
        )],  # 通过"输入集数区间"回调按钮、"获取分集"按钮或分页按钮触发
        states={
            1: [
                MessageHandler(  # INPUT_EPISODE_RANGE = 1
                    filters.TEXT & ~filters.COMMAND,
                    _wrap_with_session_management(handle_episode_range_input)
                ),
                CallbackQueryHandler(  # 处理分页按钮回调
                    _wrap_with_session_management(handle_get_episode_callback),
                    pattern=r'^.*"switch_episode_page".*$'
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", _wrap_with_session_management(cancel_episode_input)),
            CommandHandler("search", _wrap_conversation_entry_point(search_media)),
            CommandHandler("auto", _wrap_conversation_entry_point(import_auto)),
            CommandHandler("start", _wrap_with_session_management(start)),
            CommandHandler("help", _wrap_with_session_management(help_command))
        ],
        # 使用默认的 per_* 设置以避免混合处理器类型的警告
        per_chat=True,   # 每个聊天独立跟踪对话状态
        per_user=True,   # 每个用户独立跟踪对话状态
    )
    application.add_handler(episode_input_handler)
    current_handlers["episode_input_handler"] = episode_input_handler

    # 创建import_auto会话处理器
    import_auto_handler = ConversationHandler(
        entry_points=[CommandHandler("auto", _wrap_conversation_entry_point(import_auto))],
        states={
            1: [CallbackQueryHandler(  # IMPORT_AUTO_SEARCH_TYPE = 1
                _wrap_with_session_management(handle_search_type_callback)
            )],
            2: [
                MessageHandler(  # IMPORT_AUTO_KEYWORD_INPUT = 2
                    filters.TEXT & ~filters.COMMAND,
                    _wrap_with_session_management(import_auto_keyword_input)
                ),
                CallbackQueryHandler(_wrap_with_session_management(handle_media_type_callback)),
                CallbackQueryHandler(  # Handle all import_auto related callbacks
                    _wrap_with_session_management(handle_import_auto_callback),
                    pattern=r'{"action": "import_auto_.*"}'
                )
            ],
            3: [
                MessageHandler(  # IMPORT_AUTO_ID_INPUT = 3
                    filters.TEXT & ~filters.COMMAND,
                    _wrap_with_session_management(import_auto_id_input)
                ),
                CallbackQueryHandler(  # Handle all import_auto related callbacks
                    _wrap_with_session_management(handle_import_auto_callback),
                    pattern=r'{"action": "import_auto_.*"}'
                )
            ],
            4: [  # IMPORT_AUTO_SEASON_SELECTION = 4
                CallbackQueryHandler(
                    _wrap_with_session_management(handle_import_auto_callback),
                    pattern=r'(season_\d+|cancel|{"action": "import_auto_.*"})'
                )
            ],
            # 4: [  # IMPORT_AUTO_SEASON_INPUT = 4（已移除）
            #     MessageHandler(
            #         filters.TEXT & ~filters.COMMAND,
            #         _wrap_with_session_management(import_auto_season_input)
            #     ),
            #     CallbackQueryHandler(
            #         _wrap_with_session_management(handle_import_auto_callback),
            #         pattern=r'{"action": "import_auto_.*"}'
            #     )
            # ],
            # 5: [  # IMPORT_AUTO_EPISODE_INPUT = 5（已移除）
            #     MessageHandler(
            #         filters.TEXT & ~filters.COMMAND,
            #         _wrap_with_session_management(import_auto_episode_input)
            #     ),
            #     CallbackQueryHandler(
            #         _wrap_with_session_management(handle_import_auto_callback),
            #         pattern=r'{"action": "(continue_season_import|continue_episode_import|finish_import)".*}'
            #     )
            # ],
            # 6: [CallbackQueryHandler(  # IMPORT_AUTO_METHOD_SELECTION = 6（已移除）
            #     _wrap_with_session_management(handle_import_auto_callback),
            #     pattern=r'{"action": "import_auto_method".*}'
            # )],
        },
        fallbacks=[
            CommandHandler("cancel", _wrap_with_session_management(cancel)),
            CommandHandler("search", _wrap_conversation_entry_point(search_media)),
            CommandHandler("auto", _wrap_conversation_entry_point(import_auto)),
            CommandHandler("start", _wrap_with_session_management(start)),
            CommandHandler("help", _wrap_with_session_management(help_command))
        ],
        allow_reentry=True,  # 允许重新进入对话
        # 使用默认的 per_* 设置以避免混合处理器类型的警告
        per_chat=True,       # 每个聊天独立跟踪对话状态
        per_user=True,       # 每个用户独立跟踪对话状态
    )
    application.add_handler(import_auto_handler)
    current_handlers["import_auto_handler"] = import_auto_handler

    # 创建命令处理器
    start_handler = CommandHandler("start", start)
    help_handler = CommandHandler("help", help_command)
    cancel_handler = CommandHandler("cancel", cancel)
    
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(cancel_handler)
    
    current_handlers["start_handler"] = start_handler
    current_handlers["help_handler"] = help_handler
    current_handlers["cancel_handler"] = cancel_handler

    # 创建回调处理器
    import_callback_handler = CallbackQueryHandler(
        _wrap_with_session_management(handle_import_callback),
        pattern=r'{"action": "import_media".*}'
    )
    application.add_handler(import_callback_handler)
    current_handlers["import_callback_handler"] = import_callback_handler

    # 添加搜索分页回调处理器
    from callback.import_media import handle_search_page

    # 添加搜索分页回调处理器
    search_page_handler = CallbackQueryHandler(
        _wrap_with_session_management(handle_search_page),
        pattern=r'{"action": "search_page".*}'
    )
    application.add_handler(search_page_handler)
    current_handlers["search_page_handler"] = search_page_handler

    get_episode_callback_handler = CallbackQueryHandler(
        _wrap_with_session_management(handle_get_episode_callback),
        pattern=r'{"(action|a)": "(get_media_episode|switch_episode_page|start_input_range)".*}'
    )
    application.add_handler(get_episode_callback_handler)
    current_handlers["get_episode_callback_handler"] = get_episode_callback_handler

    # 添加import_auto回调处理器到application
    application.add_handler(import_auto_callback_handler)
    current_handlers["import_auto_callback_handler"] = import_auto_callback_handler
    
    # 创建并注册import_url处理器
    import_url_handler = create_import_url_handler()
    application.add_handler(import_url_handler)
    current_handlers["import_url_handler"] = import_url_handler
    
    # 导入并注册token管理处理器
    from handlers.token_management import create_token_management_handler
    token_management_handler = create_token_management_handler()
    application.add_handler(token_management_handler)
    current_handlers["token_management_handler"] = token_management_handler

    # 导入并注册用户管理处理器
    from handlers.user_management import create_user_management_handlers
    user_management_handlers = create_user_management_handlers()
    for name, handler in user_management_handlers:
        application.add_handler(handler)
        current_handlers[name] = handler

    # 导入并注册配额查询处理器
    from handlers.quota import create_quota_handler
    quota_handler = create_quota_handler()
    application.add_handler(quota_handler)
    current_handlers["quota_handler"] = quota_handler

    # 导入并注册refresh处理器
    from handlers.refresh_sources import create_refresh_handler
    refresh_handler = create_refresh_handler()
    application.add_handler(refresh_handler)
    current_handlers["refresh_handler"] = refresh_handler
    
    # 导入并注册refresh回调处理器
    from callback.refresh_sources import handle_refresh_callback_query
    refresh_callback_handler = CallbackQueryHandler(
        _wrap_with_session_management(handle_refresh_callback_query),
        pattern=r'refresh_(full|episode)_.*'
    )
    application.add_handler(refresh_callback_handler)
    current_handlers["refresh_callback_handler"] = refresh_callback_handler


async def init_bot() -> Application:
    """创建机器人应用实例，并完成初始处理器注册"""
    # 步骤1: 使用我们新的导入函数，获取最新的模块引用
    config_manager, handlers, callback = _import_modules()

    # 步骤2: 创建 Telegram 机器人应用
    builder = ApplicationBuilder().token(config_manager.telegram.bot_token)
    
    # 配置连接超时（使用Telegram专用配置）
    builder = builder.connect_timeout(config_manager.telegram.connect_timeout).read_timeout(config_manager.telegram.read_timeout).write_timeout(config_manager.telegram.read_timeout)
    
    # 配置连接池（使用配置文件中的值，解决连接池占满的问题）
    builder = builder.pool_timeout(config_manager.telegram.pool_timeout).connection_pool_size(config_manager.telegram.connection_pool_size)
    
    # 配置网络重试机制和getUpdates专用连接池
    builder = builder.get_updates_connect_timeout(config_manager.telegram.connect_timeout).get_updates_read_timeout(config_manager.telegram.read_timeout).get_updates_pool_timeout(config_manager.telegram.pool_timeout).get_updates_connection_pool_size(config_manager.telegram.connection_pool_size)
    
    # 配置代理（基于Docker环境变量）
    if config_manager.proxy and config_manager.proxy.enabled:
        proxy_url = config_manager.proxy.url
        logger.info(f"🌐 Using proxy from Docker environment: {proxy_url}")
        builder = builder.proxy(proxy_url)
    else:
        logger.info("🌐 No proxy configured, using direct connection")
    
    application = builder.build()

    # 步骤3: 注册错误处理器
    application.add_error_handler(error_handler)
    logger.info("✅ Global error handler registered")
    
    # 步骤4: 注册初始处理器
    _setup_handlers(application, handlers, callback)

    # 步骤5: 设置 Bot 命令菜单
    await _setup_bot_commands(application)
    
    # 步骤6: 初始化弹幕库缓存
    try:
        from handlers.import_url import init_library_cache
        await init_library_cache()
    except Exception as e:
        logger.warning(f"⚠️ 影视库缓存初始化失败: {e}")

    logger.info("✅ Initial bot handlers registered")
    return application

# ------------------------------
# 3. 热更新服务启动（文件监听线程）
# ------------------------------
def start_file_observer(application: Application) -> Observer:
    """启动文件监听服务，独立线程运行"""
    loop = asyncio.get_event_loop()
    event_handler = CodeChangeHandler(application, loop)
    observer = Observer()

    for dir_path in WATCHED_DIRS:
        if dir_path.exists():
            observer.schedule(
                event_handler,
                path=str(dir_path),
                recursive=True
            )
            logger.info(f"ℹ️ Hot reload watching enabled for: {dir_path}")
        else:
            logger.warning(f"⚠️ Hot reload directory does not exist, skipping: {dir_path}")

    observer.start()
    return observer

# ------------------------------
# 4. 主程序入口（机器人启动+热更新服务）
# ------------------------------
if __name__ == "__main__":
    import signal
    
    # 全局变量用于存储需要清理的资源
    file_observer = None
    application = None
    
    async def cleanup_resources(app):
        """清理所有资源的异步函数"""
        logger.info("🛑 开始清理资源...")
        
        # 停止热重载服务
        if file_observer is not None:
            try:
                file_observer.stop()
                file_observer.join()
                logger.info("🔍 Hot reload service stopped")
            except Exception as e:
                logger.error(f"❌ 停止热重载服务时出错: {e}")
    
    def signal_handler(signum, frame):
        """信号处理器，用于优雅地停止应用程序"""
        logger.info(f"\n🛑 Received signal {signum}, starting graceful shutdown...")
        if application is not None:
            application.stop_running()
    
    try:
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        application = loop.run_until_complete(init_bot())
        logger.info("🚀 Bot application initialization complete")
        
        # 获取配置管理器
        config_manager, _, _ = _import_modules()
        
        # 设置 post_shutdown 回调来清理资源
        application.post_shutdown = cleanup_resources
        
        # 热重载功能（仅在开发环境启用）
        # 根据ENVIRONMENT环境变量决定是否启用热重载
        environment = os.getenv('ENVIRONMENT', config_manager.app.environment).lower()
        enable_hot_reload = environment == 'development'

        if enable_hot_reload:
            file_observer = start_file_observer(application)
            logger.info("🔍 Hot reload service started: changes to handlers/utils/config will take effect automatically")
        else:
            logger.info("🔒 Hot reload disabled for production environment")

        logger.info("📡 Bot has started listening for commands (press Ctrl+C to exit gracefully)")
        

        
        # 启动bot应用
        loop.run_until_complete(application.run_polling())
        
    except Exception as e:
        logger.error(f"❌ Bot failed to start! Error: {str(e)}", exc_info=True)
        # 在异常情况下手动清理资源（仅在事件循环未关闭时）

        
        if file_observer is not None:
            try:
                file_observer.stop()
                file_observer.join()
                logger.info("🔍 Hot reload service stopped (exception cleanup)")
            except Exception as cleanup_error:
                logger.error(f"❌ 异常清理时停止热重载服务出错: {cleanup_error}")
    
    finally:
        # 最终清理阶段
        if application is not None and not loop.is_closed():
            try:
                loop.run_until_complete(application.shutdown())
                logger.info("🚀 Bot application shut down")
            except Exception as e:
                logger.error(f"❌ 关闭应用程序时出错: {e}")
        
        if 'loop' in locals() and not loop.is_closed():
            try:
                loop.close()
                logger.info("✅ Event loop closed")
            except Exception as e:
                logger.error(f"❌ 关闭事件循环时出错: {e}")
        
        logger.info("✅ All services have exited normally")
