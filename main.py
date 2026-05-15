import os
import uuid
import logging
import threading
from flask import Flask # اضافه شدن فلسک برای وب‌سرور
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler
)

# --------------------- تنظیمات وب‌سرور برای رندر ---------------------
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "Bot is running!", 200

def run_web_server():
    port = int(os.environ.get('PORT', 5000))
    web_app.run(host='0.0.0.0', port=port)
# --------------------------------------------------------

# --------------------- تنظیمات لاگ ---------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --------------------- تنظیمات قالب‌ها ---------------------
TEMPLATES = {
    "classic_no_title": {
        "name": "بدون عنوان",
        "group": "classic",
        "image": "templates/NoTitle.png",
        "has_title": False,
        "text_config": {
            "font": "fonts/Bahij TheSansArabic-Bold.ttf",
            "size_short": 69,
            "size_long": 42,
            "max_width": 830,
            "max_width_short": 830,
            "position": [80, 230],
            "position_short": [80, 230],
            "color": "white",
            "line_spacing": 20,
            "max_lines_short": 4,
            "max_lines_long": 5
        }
    },
    "classic_with_title": {
        "name": "با عنوان",
        "group": "classic",
        "image": "templates/WithTitle.png",
        "has_title": True,
        "text_config": {
            "font": "fonts/Bahij TheSansArabic-Bold.ttf",
            "size_short": 69,
            "size_long": 42,
            "max_width": 830,
            "max_width_short": 830,
            "position": [80, 230],
            "position_short": [80, 230],
            "color": "white",
            "line_spacing": 20,
            "max_lines_short": 4,
            "max_lines_long": 5
        },
        "title_config": {
            "font": "fonts/Bahij TheSansArabic-Bold.ttf",
            "size": 36,
            "max_width": 400,
            "position": [125, 120],
            "color": "black",
            "line_spacing": 5
        }
    },
    "new_template": {
        "name": "قالب دوم",
        "group": "new",
        "image": "templates/NewT.png",
        "has_title": False,
        "text_config": {
            "font": "fonts/Bahij TheSansArabic-Black.ttf",
            "size_short": 66,
            "size_long": 50,
            "max_width": 830,
            "max_width_short": 830,
            "position": [150, 658],
            "position_short": [150, 658],
            "color": "white",
            "line_spacing": 13,
            "max_lines_short": 3,
            "max_lines_long": 4
        }
    },
    "template_3_vcenter": {
        "name": "قالب سوم",
        "group": "new",
        "image": "templates/T3.png",
        "has_title": False,
        "text_config": {
            "font_short": "fonts/Bahij TheSansArabic-Black.ttf",
            "font_long": "fonts/Bahij TheSansArabic-ExtraBold.ttf",
            "size_short": 64,
            "size_long": 46,
            "max_width": 830,
            "max_width_short": 830,
            "text_box": [150, 860, 980, 850],
            "color": "white",
            "line_spacing": 17,
            "max_lines_short": 3,
            "max_lines_long": 4,
            "vertical_align": "middle"
        }
    },
}

# توکن حالا از متغیرهای محیطی خوانده میشه
TOKEN = os.environ.get("BOT_TOKEN") 
ADMIN_ID = 1633475675
(HOME, CHOOSE_TEMPLATE_TYPE, SELECT_CLASSIC_TEMPLATE, GET_TITLE, GET_PHOTO, GET_TEXT_LENGTH, GET_TEXT) = range(7)

def home_keyboard():
    return ReplyKeyboardMarkup(
        [["🎨 إنشاء منشور جديد"]],
        resize_keyboard=True,
        input_field_placeholder="للبدء، اضغط على /start"
    )

def template_type_keyboard():
    return ReplyKeyboardMarkup(
        [["قالب اول", "قالب دوم"], ["قالب سوم"], ["🔙 رجوع"]],
        resize_keyboard=True
    )

def classic_template_keyboard():
    return ReplyKeyboardMarkup(
        [["با عنوان", "بدون عنوان"], ["🔙 رجوع"]],
        resize_keyboard=True
    )

def text_length_keyboard():
    return ReplyKeyboardMarkup(
        [["نص قصير"], ["نص طويل"], ["🔙 رجوع"]],
        resize_keyboard=True
    )

# --------------------- توابع کمکی ---------------------
def prepare_background_image(user_image, template_size, template_info):
    template_w, template_h = template_size
    user_w, user_h = user_image.size
    resampling_filter = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS

    if template_info['group'] == 'new':
        user_aspect = user_w / user_h
        template_aspect = template_w / template_h
        if user_aspect > template_aspect:
            new_h = template_h
            new_w = int(new_h * user_aspect)
            resized_image = user_image.resize((new_w, new_h), resampling_filter)
            left = (new_w - template_w) // 2
            top = 0
            right = left + template_w
            bottom = template_h
            return resized_image.crop((left, top, right, bottom))
        else:
            new_w = template_w
            new_h = int(new_w / user_aspect)
            resized_image = user_image.resize((new_w, new_h), resampling_filter)
            left = 0
            top = (new_h - template_h) // 2
            right = template_w
            bottom = top + template_h
            return resized_image.crop((left, top, right, bottom))
    else:
        background = Image.new("RGBA", template_size)
        if user_w >= template_w and user_h >= template_h:
            left = (user_w - template_w) // 2
            top = user_h - template_h
            right = left + template_w
            bottom = user_h
            cropped_image = user_image.crop((left, top, right, bottom))
            background.paste(cropped_image, (0, 0))
        else:
            target_h = (template_h / 2) + 300
            scale_by_height_factor = target_h / user_h
            new_w_by_height = int(user_w * scale_by_height_factor)
            if new_w_by_height < template_w:
                scale_by_width_factor = template_w / user_w
                final_w = template_w
                final_h = int(user_h * scale_by_width_factor)
            else:
                final_w = new_w_by_height
                final_h = int(target_h)
            resized_image = user_image.resize((final_w, final_h), resampling_filter)
            paste_x = (template_w - final_w) // 2
            paste_y = template_h - final_h
            background.paste(resized_image, (paste_x, paste_y))
        return background


def text_wrap(text, font, max_width, max_lines):
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = f"{current_line} {word}".strip()
        if font.getbbox(test_line)[2] <= max_width:
            current_line = test_line
        else:
            if len(lines) < max_lines - 1:
                lines.append(current_line)
                current_line = word
            else:
                while font.getbbox(current_line + '...')[2] > max_width:
                    current_line = current_line[:-1]
                current_line += '...'
                break
    if current_line:
        lines.append(current_line)
    return lines[:max_lines]

def draw_right_aligned_text(draw, lines, position, font, fill, line_spacing):
    y_position = position[1]
    template_width = draw.im.size[0]
    right_margin = position[0]
    for line in lines:
        line_width = font.getbbox(line)[2]
        x = template_width - right_margin - line_width
        draw.text((x, y_position), line, font=font, fill=fill, direction="rtl")
        y_position += font.getmetrics()[0] + line_spacing

def draw_vertically_centered_text(draw, lines, text_box, font, fill, line_spacing):
    line_height = font.getmetrics()[0]
    total_text_height = (len(lines) * line_height) + ((len(lines) - 1) * line_spacing) if len(lines) > 1 else line_height
    y = text_box[1] + (text_box[3] - text_box[1] - total_text_height) / 2

    right_margin = text_box[0]
    template_width = draw.im.size[0]
    for line in lines:
        line_width = font.getbbox(line)[2]
        x = template_width - right_margin - line_width
        draw.text((x, y), line, font=font, fill=fill, direction="rtl")
        y += line_height + line_spacing

def generate_final_image(user_data):
    try:
        template = TEMPLATES[user_data['template']]
        base_image = Image.open(template['image']).convert("RGBA")
        user_img = Image.open(user_data['photo_path']).convert("RGBA")

        background_image = prepare_background_image(user_img, base_image.size, template)
        final_image = Image.alpha_composite(background_image, base_image)
        draw = ImageDraw.Draw(final_image)

        if template['has_title']:
            cfg = template['title_config']
            title_font = ImageFont.truetype(cfg['font'], cfg['size'])
            title_lines = text_wrap(user_data['title'], title_font, cfg['max_width'], 1)
            title_spacing = cfg.get('line_spacing', 5)
            draw_right_aligned_text(draw, title_lines, cfg['position'], title_font, cfg['color'], title_spacing)

        cfg = template['text_config']
        text = user_data["text"]
        text_length = user_data["text_length"]

        if 'font_short' in cfg and 'font_long' in cfg:
            font_path = cfg['font_short'] if text_length == "نص قصير" else cfg['font_long']
        else:
            font_path = cfg['font']

        font_size = cfg['size_short'] if text_length == "نص قصير" else cfg['size_long']
        max_width = cfg['max_width_short'] if text_length == "نص قصير" else cfg['max_width']
        max_lines = cfg['max_lines_short'] if text_length == "نص قصير" else cfg['max_lines_long']

        font = ImageFont.truetype(font_path, font_size)
        lines = text_wrap(text, font, max_width, max_lines)
        text_spacing = cfg.get('line_spacing', 10)

        if cfg.get('vertical_align') == 'middle':
            draw_vertically_centered_text(draw, lines, cfg['text_box'], font, cfg['color'], text_spacing)
        else:
            position = cfg['position_short'] if text_length == "نص قصير" else cfg['position']
            draw_right_aligned_text(draw, lines, position, font, cfg['color'], text_spacing)

        output_path = f"output_{uuid.uuid4()}.png"
        final_image.save(output_path)
        return output_path
    except Exception as e:
        logger.error(f"خطأ في إنشاء المنشور: {e}", exc_info=True)
        return None

def cleanup_files(user_data):
    for key in ['photo_path', 'output_path']:
        if key in user_data and user_data[key]:
            try:
                if os.path.exists(user_data[key]):
                    os.remove(user_data[key])
                    logger.info(f"تم حذف الملف {user_data[key]}")
            except Exception as e:
                logger.error(f"خطأ في حذف الملف {user_data[key]}: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "✨ أهلاً بك في البوت 👋\nللاستخدام، اضغط على زر إنشاء منشور جديد.",
        reply_markup=home_keyboard()
    )
    return HOME

async def start_new_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "📜 يرجى اختيار نوع القالب:",
        reply_markup=template_type_keyboard()
    )
    return CHOOSE_TEMPLATE_TYPE

async def choose_template_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.strip()
    if choice == "قالب اول":
        await update.message.reply_text("اختر نوع القالب الأول:", reply_markup=classic_template_keyboard())
        return SELECT_CLASSIC_TEMPLATE
    elif choice == "قالب دوم":
        context.user_data['template'] = 'new_template'
        await update.message.reply_text("١️⃣ أرسل الصورة 📷", reply_markup=ReplyKeyboardMarkup([["🔙 رجوع"]], resize_keyboard=True))
        return GET_PHOTO
    elif choice == "قالب سوم":
        context.user_data['template'] = 'template_3_vcenter'
        await update.message.reply_text("١️⃣ أرسل الصورة 📷", reply_markup=ReplyKeyboardMarkup([["🔙 رجوع"]], resize_keyboard=True))
        return GET_PHOTO
    elif choice == "🔙 رجوع":
        await update.message.reply_text("القائمة الرئيسية:", reply_markup=home_keyboard())
        return HOME
    else:
        await update.message.reply_text("⚠️ الرجاء استخدام الخيارات المتاحة!", reply_markup=template_type_keyboard())
        return CHOOSE_TEMPLATE_TYPE

async def select_classic_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.strip()
    if choice == "با عنوان":
        context.user_data['template'] = 'classic_with_title'
        await update.message.reply_text("١️⃣ أرسل العنوان أولاً ✍️", reply_markup=ReplyKeyboardMarkup([["🔙 رجوع"]], resize_keyboard=True))
        return GET_TITLE
    elif choice == "بدون عنوان":
        context.user_data['template'] = 'classic_no_title'
        await update.message.reply_text("١️⃣ أرسل الصورة 📷", reply_markup=ReplyKeyboardMarkup([["🔙 رجوع"]], resize_keyboard=True))
        return GET_PHOTO
    elif choice == "🔙 رجوع":
        await update.message.reply_text("📜 يرجى اختيار نوع القالب:", reply_markup=template_type_keyboard())
        return CHOOSE_TEMPLATE_TYPE
    else:
        await update.message.reply_text("⚠️ الرجاء استخدام الخيارات المتاحة!", reply_markup=classic_template_keyboard())
        return SELECT_CLASSIC_TEMPLATE

async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔙 رجوع":
        await update.message.reply_text("اختر نوع القالب الأول:", reply_markup=classic_template_keyboard())
        return SELECT_CLASSIC_TEMPLATE
    context.user_data['title'] = update.message.text.strip()
    await update.message.reply_text("٢️⃣ أرسل الصورة 📷", reply_markup=ReplyKeyboardMarkup([["🔙 رجوع"]], resize_keyboard=True))
    return GET_PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text and update.message.text == "🔙 رجوع":
        template_key = context.user_data.get('template')
        if not template_key:
            return await start_new_post(update, context)

        template = TEMPLATES[template_key]
        if template['has_title']:
            await update.message.reply_text("١️⃣ أرسل العنوان أولاً ✍️", reply_markup=ReplyKeyboardMarkup([["🔙 رجوع"]], resize_keyboard=True))
            return GET_TITLE
        elif template['group'] == 'classic':
             await update.message.reply_text("اختر نوع القالب الأول:", reply_markup=classic_template_keyboard())
             return SELECT_CLASSIC_TEMPLATE
        else:
            await update.message.reply_text("📜 يرجى اختيار نوع القالب:", reply_markup=template_type_keyboard())
            return CHOOSE_TEMPLATE_TYPE

    try:
        photo_file = None
        if update.message.photo:
            photo_file = await update.message.photo[-1].get_file()
        elif update.message.document:
            photo_file = await update.message.document.get_file()

        if not photo_file:
            await update.message.reply_text("❌ فرمت ارسالی پشتیبانی نمی‌شود. لطفاً یک عکس ارسال کنید.")
            return GET_PHOTO

        unique_id = str(uuid.uuid4())
        photo_path = f"temp_{unique_id}.png"
        await photo_file.download_to_drive(photo_path)
        context.user_data['photo_path'] = photo_path
    except Exception as e:
        logger.error(f"خطأ في استلام الصورة: {e}")
        await update.message.reply_text("❌ خطأ في استلام الصورة. يرجى المحاولة مرة أخرى.")
        return GET_PHOTO

    template = TEMPLATES[context.user_data['template']]
    next_step_number = "٣️⃣" if template['has_title'] else "٢️⃣"
    await update.message.reply_text(
        f"{next_step_number} اختر طول النص:",
        reply_markup=text_length_keyboard()
    )
    return GET_TEXT_LENGTH

async def get_text_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.strip()
    if choice == "🔙 رجوع":
        template = TEMPLATES[context.user_data['template']]
        previous_step_number = "٢️⃣" if template['has_title'] else "١️⃣"
        await update.message.reply_text(f"{previous_step_number} أرسل الصورة 📷", reply_markup=ReplyKeyboardMarkup([["🔙 رجوع"]], resize_keyboard=True))
        return GET_PHOTO

    if choice not in ["نص قصير", "نص طويل"]:
        await update.message.reply_text("⚠️ الرجاء استخدام الخيارات المتاحة!", reply_markup=text_length_keyboard())
        return GET_TEXT_LENGTH

    context.user_data['text_length'] = choice
    template = TEMPLATES[context.user_data['template']]
    next_step_number = "٤️⃣" if template['has_title'] else "٣️⃣"
    await update.message.reply_text(
        f"{next_step_number} أرسل النص الآن ✉️",
        reply_markup=ReplyKeyboardMarkup([["🔙 رجوع"]], resize_keyboard=True)
    )
    return GET_TEXT

async def get_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔙 رجوع":
        template = TEMPLATES[context.user_data['template']]
        previous_step_number = "٣️⃣" if template['has_title'] else "٢️⃣"
        await update.message.reply_text(f"{previous_step_number} اختر طول النص:", reply_markup=text_length_keyboard())
        return GET_TEXT_LENGTH

    context.user_data['text'] = update.message.text.strip()
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    output_path = generate_final_image(context.user_data)
    context.user_data['output_path'] = output_path

    if output_path and os.path.exists(output_path):
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
        try:
            await update.message.reply_photo(
                photo=open(output_path, 'rb'),
                caption="✅ تم إنشاء المنشور بنجاح!\n\nلإنشاء منشور جديد، اضغط على الزر أدناه.",
                reply_markup=home_keyboard()
            )
        except Exception as e:
            logger.error(f"خطأ في إرسال المنشور: {e}")
            await update.message.reply_text("❌ خطأ في إرسال المنشور!", reply_markup=home_keyboard())
    else:
        await update.message.reply_text("❌ خطأ في إنشاء المنشور!", reply_markup=home_keyboard())

    cleanup_files(context.user_data)
    context.user_data.clear()
    return HOME

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cleanup_files(context.user_data)
    context.user_data.clear()
    await update.message.reply_text(
        'عملیات لغو شد.', reply_markup=home_keyboard()
    )
    return HOME


def main():
    """Start the bot."""
    if not os.path.exists("templates"):
        os.makedirs("templates")
    if not os.path.exists("fonts"):
        os.makedirs("fonts")

    # ۱. استارت زدن وب‌سرور تو یک ترد جداگانه برای رندر
    threading.Thread(target=run_web_server, daemon=True).start()

    # ۲. بررسی وجود توکن
    if not TOKEN:
        logger.error("BOT_TOKEN environment variable not set!")
        return

    # ۳. اجرای پولینگ ربات
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            HOME: [MessageHandler(filters.Regex(r'^🎨 إنشاء منشور جديد$'), start_new_post)],
            CHOOSE_TEMPLATE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_template_type)],
            SELECT_CLASSIC_TEMPLATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_classic_template)],
            GET_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
            GET_PHOTO: [MessageHandler((filters.PHOTO | filters.Document.IMAGE | (filters.TEXT & ~filters.COMMAND)), get_photo)],
            GET_TEXT_LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_text_length)],
            GET_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_text)]
        },
        fallbacks=[CommandHandler('start', start), CommandHandler('cancel', cancel)],
        allow_reentry=True
    )
    app.add_handler(conv_handler)
    
    logger.info("Starting polling...")
    app.run_polling()

if __name__ == "__main__":
    main()