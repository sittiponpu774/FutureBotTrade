from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from telegram import Update
from dotenv import load_dotenv
import os
from src.routes.predict import predict_coin
from src.routes.trading import create_position

ASK_POSITION, ASK_POSITION_DETAILS = range(2)

def build_bot():
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("พิมพ์ชื่อเหรียญ เช่น btc/usdt 1h เพื่อทำนายราคา")

    async def handle_predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip().lower()
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text("กรุณาพิมพ์ในรูปแบบ: symbol timeframe เช่น btc/usdt 1h")
            return ASK_POSITION  # อยู่ใน state รอ input ใหม่

        symbol, timeframe = parts
        result = predict_coin(symbol, timeframe)
        msg = (
            f"ราคาล่าสุด: {result['price']}\n"
            f"ความแม่นยำ: {result['accuracy']}%\n"
            f"คำแนะนำ: {result['recommendation']}\n"
            "ต้องการสร้าง position เลยมั้ย? (y/n)"
        )
        context.user_data['predict_result'] = result
        await update.message.reply_text(msg)
        return ASK_POSITION_DETAILS

    async def handle_create_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
        print("[DEBUG] ✳️ handle_create_position ถูกเรียก")
        text = update.message.text.strip().lower()
        if text == 'y':
            await update.message.reply_text(
                "กรุณาพิมพ์ข้อมูล entry_price profit_target loss_limit คั่นด้วยเว้นวรรค เช่น\n100.5 110.0 90.0"
            )
            return ASK_POSITION_DETAILS
        elif text == 'n':
            await update.message.reply_text("❌ ยกเลิกการสร้าง position")
            return ConversationHandler.END
        else:
            await update.message.reply_text("กรุณาพิมพ์ y หรือ n เท่านั้น")
            return ASK_POSITION

    async def handle_position_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        try:
            entry_price_str, profit_target_str, loss_limit_str = text.split()
            entry_price = float(entry_price_str)
            profit_target = float(profit_target_str)
            loss_limit = float(loss_limit_str)
        except Exception:
            await update.message.reply_text("❌ ข้อมูลไม่ถูกต้อง กรุณาพิมพ์ใหม่ เช่น 100.5 110.0 90.0")
            return ASK_POSITION_DETAILS

        result = context.user_data['predict_result']
        create_position(
            symbol=result['symbol'],
            timeframe=result['timeframe'],
            position_type=result['recommendation'],
            entry_price=entry_price,
            entry_time=result['predict_time'],
            profit_target=profit_target,
            loss_limit=loss_limit,
            telegram_user=update.effective_user.username
        )
        await update.message.reply_text("✅ สร้าง position สำเร็จ!")
        return ConversationHandler.END

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler('start', start))

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_predict)],
        states={
            ASK_POSITION: [MessageHandler(filters.Regex('^(y|n|Y|N)$'), handle_create_position)],
            ASK_POSITION_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_position_details)],
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True,
    )
    app.add_handler(conv_handler)

    return app
