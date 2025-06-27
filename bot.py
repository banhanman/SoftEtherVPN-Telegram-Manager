import os
import subprocess
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Updater, 
    CommandHandler, 
    CallbackContext,
    MessageHandler,
    Filters
)

# Конфигурация (замените значения на свои!)
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
ALLOWED_USER_IDS = [123456789]  # Ваш Telegram ID
VPN_SERVER_IP = "your.vpn.server.ip"
VPN_HUB = "VPN"
VPN_MANAGEMENT_PORT = 5555
VPN_ADMIN_PASSWORD = "your_hub_password"

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ======================
# VPN УТИЛИТЫ (vcmd)
# ======================
def run_vpn_command(command):
    """Выполняет команду через vcmd и возвращает результат"""
    try:
        cmd = f'vcmd -server {VPN_SERVER_IP}:{VPN_MANAGEMENT_PORT} -hub {VPN_HUB} -password {VPN_ADMIN_PASSWORD} {command}'
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        return result.stdout.strip() if result.returncode == 0 else f"Error: {result.stderr.strip()}"
    except Exception as e:
        return f"Command failed: {str(e)}"

def create_user(username, password):
    """Создает нового VPN пользователя"""
    return run_vpn_command(f'user create {username} /GROUP:none /REALNAME:TelegramBot /NOTE:AutoCreated /AUTHTYPE:password /PASSWORD:{password}')

def delete_user(username):
    """Удаляет пользователя VPN"""
    return run_vpn_command(f'user delete {username}')

def rename_user(old_name, new_name):
    """Переименовывает пользователя VPN"""
    return run_vpn_command(f'user set {old_name} /newname:{new_name}')

def set_speed_limit(username, mbps):
    """Устанавливает лимит скорости (в Мбит/с)"""
    bytes_per_sec = int(mbps) * 125000  # Конвертация в байты/сек
    return run_vpn_command(f'traffic set {username} /MAXUPTRAFFIC:{bytes_per_sec} /MAXDOWNTRAFFIC:{bytes_per_sec}')

def disconnect_user(username):
    """Отключает активные сессии пользователя"""
    return run_vpn_command(f'session disconnect /USERNAME:{username}')

def block_user(username):
    """Блокирует доступ пользователя"""
    return run_vpn_command(f'user set {username} /DISABLED:yes')

def unblock_user(username):
    """Разблокирует пользователя"""
    return run_vpn_command(f'user set {username} /DISABLED:no')

def list_users():
    """Возвращает список пользователей"""
    return run_vpn_command('user list')

# ======================
# TELEGRAM БОТ
# ======================
def restricted(func):
    """Декоратор для ограничения доступа"""
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ALLOWED_USER_IDS:
            update.message.reply_text("🚫 Access Denied!")
            return
        return func(update, context, *args, **kwargs)
    return wrapper

@restricted
def start(update: Update, context: CallbackContext):
    """Обработка команды /start"""
    user = update.effective_user
    keyboard = [['/list_users', '/help']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    update.message.reply_markdown_v2(
        f"👋 Welcome *{user.first_name}* to VPN Manager\!\n"
        "Use /help for available commands",
        reply_markup=reply_markup
    )

@restricted
def help_command(update: Update, context: CallbackContext):
    """Обработка команды /help"""
    help_text = """
🔐 *VPN Management Bot* 🔐
    
*/start* - Start bot
*/help* - Show this help
*/add_user <username> <password>* - Create new VPN user
*/del_user <username>* - Delete VPN user
*/rename_user <old> <new>* - Rename user
*/set_speed <username> <mbps>* - Set speed limit (Mbps)
*/disconnect <username>* - Disconnect user sessions
*/block_user <username>* - Block user access
*/unblock_user <username>* - Unblock user
*/list_users* - Show all VPN users
*/status <username>* - Show user details
"""
    update.message.reply_markdown_v2(help_text)

@restricted
def add_user(update: Update, context: CallbackContext):
    """Добавление пользователя VPN"""
    if len(context.args) < 2:
        update.message.reply_text("❌ Usage: /add_user <username> <password>")
        return
    
    username, password = context.args[0], context.args[1]
    result = create_user(username, password)
    update.message.reply_text(f"✅ User *{username}* created!\n{result}", parse_mode='Markdown')

@restricted
def delete_user_cmd(update: Update, context: CallbackContext):
    """Удаление пользователя VPN"""
    if not context.args:
        update.message.reply_text("❌ Usage: /del_user <username>")
        return
    
    username = context.args[0]
    result = delete_user(username)
    update.message.reply_text(f"🗑️ User *{username}* deleted!\n{result}", parse_mode='Markdown')

# ... (аналогичные обработчики для других команд)

@restricted
def list_users_cmd(update: Update, context: CallbackContext):
    """Список пользователей VPN"""
    users = list_users()
    update.message.reply_text(f"📋 VPN Users:\n```\n{users}\n```", parse_mode='MarkdownV2')

def error_handler(update: Update, context: CallbackContext):
    """Обработка ошибок"""
    logger.error(f"Update {update} caused error: {context.error}")
    if update.message:
        update.message.reply_text("⚠️ An error occurred. Please check logs.")

def main():
    """Запуск бота"""
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    # Регистрация обработчиков команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("add_user", add_user))
    dp.add_handler(CommandHandler("del_user", delete_user_cmd))
    dp.add_handler(CommandHandler("list_users", list_users_cmd))
    # ... (добавить остальные команды)

    dp.add_error_handler(error_handler)
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
