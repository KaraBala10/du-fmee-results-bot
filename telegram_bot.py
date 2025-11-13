import asyncio
import logging
import os
import re
import sys
import threading
import time
from datetime import datetime
from waitress import serve

import requests
import urllib3
from dotenv import load_dotenv
from flask import Flask

# Load environment variables
load_dotenv()

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import Conflict, NetworkError, TimedOut
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# Flask app (for hosting/health check)
app = Flask(__name__)


@app.route("/")
def index():
    return "Bot is running ✅", 200


# Bot token from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN not found in environment variables. Please check your .env file."
    )

# Create a session for better connection handling
session = requests.Session()
session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ar,en-US;q=0.7,en;q=0.3",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
)

# Configure session for better reliability
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Department mapping
DEPARTMENTS = {
    "1": "هندسة الإلكترونيات والاتصالات",
    "2": "هندسة الحواسيب والأتمتة",
    "3": "هندسة الطاقة الكهربائية",
    "4": "هندسة التصميم الميكانيكي",
    "5": "الهندسة الطبية",
    "6": "هندسة الميكانيك العام",
    "7": "هندسة ميكانيك الصناعات النسيجية وتقاناتها",
    "8": "هندسة السيارات والآليات الثقيلة",
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    logger.info("start command called")
    welcome_text = """
🎓 مرحباً بك في بوت علاماتي - نتائج جامعة دمشق
كلية الهندسة الميكانيكية والكهربائية - قسم هندسة الحواسيب والأتمتة

يمكنك الحصول على نتائجك الامتحانية بسهولة!

📋 الأوامر المتاحة:
/help - المساعدة
/get_marks - الحصول على النتائج
    """
    await update.message.reply_text(welcome_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    logger.info("help command called")
    help_text = """
🔍 كيفية استخدام بوت علاماتي:

1️⃣ أرسل رقمك الجامعي "وليس الامتحاني"
2️⃣ اختر السنة الدراسية
3️⃣ احصل على نتائجك!

📞 للدعم: تواصل مع المطور @karabala10
    """
    await update.message.reply_text(help_text)


async def get_marks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the marks retrieval process."""
    logger.info("get_marks_command called")
    await update.message.reply_text("📝 أرسل رقمك الجامعي للحصول على النتائج:")


async def handle_student_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle student number input."""
    student_number = update.message.text.strip()

    logger.info(f"handle_student_number called with: {student_number}")

    # Validate student number
    if not re.match(r"^\d{10}$", student_number):
        await update.message.reply_text("❌ رقم جامعي غير صحيح. يجب أن يكون 10 أرقام.")
        return

    # Store student number in context
    context.user_data["student_number"] = student_number
    logger.info(f"Student number stored: {student_number}")

    # Create academic year selection keyboard
    keyboard = [
        [InlineKeyboardButton("السنة الأولى", callback_data="academic_year_1")],
        [InlineKeyboardButton("السنة الثانية", callback_data="academic_year_2")],
        [InlineKeyboardButton("السنة الثالثة", callback_data="academic_year_3")],
        [
            InlineKeyboardButton(
                "السنة الرابعة - حواسيب", callback_data="academic_year_4_computer"
            )
        ],
        [
            InlineKeyboardButton(
                "السنة الرابعة - تحكم", callback_data="academic_year_4_control"
            )
        ],
        [
            InlineKeyboardButton(
                "السنة الخامسة - حواسيب", callback_data="academic_year_5_computer"
            )
        ],
        [
            InlineKeyboardButton(
                "السنة الخامسة - تحكم", callback_data="academic_year_5_control"
            )
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ رقمك الجامعي: {student_number}\n\n📚 اختر السنة الدراسية:",
        reply_markup=reply_markup,
    )


async def handle_academic_year_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Handle academic year selection."""
    query = update.callback_query
    await query.answer()

    logger.info("handle_academic_year_selection called")
    logger.info(f"Query data: {query.data}")

    academic_year_data = query.data.split("_")[2:]  # Get year and specialization
    academic_year = academic_year_data[0]
    specialization = academic_year_data[1] if len(academic_year_data) > 1 else None

    logger.info(f"Academic year: {academic_year}, Specialization: {specialization}")

    # Store academic year info
    context.user_data["academic_year"] = academic_year
    context.user_data["specialization"] = specialization

    # Automatically select department 2 (هندسة الحواسيب والأتمتة)
    context.user_data["department_id"] = "2"

    # Show loading message and proceed directly to fetch marks
    year_display = f"السنة {academic_year}"
    if specialization:
        specialization_display = "حواسيب" if specialization == "computer" else "تحكم"
        year_display += f" - {specialization_display}"

    await query.edit_message_text(
        f"✅ السنة المختارة: {year_display}\n✅ القسم: هندسة الحواسيب والأتمتة\n\n⏳ جاري جلب النتائج..."
    )

    # Fetch marks directly instead of calling handle_department_selection
    try:
        # Fetch all years data
        logger.info(
            f"Fetching data for student: {context.user_data['student_number']}, department: {context.user_data['department_id']}"
        )
        all_marks_data = await fetch_student_marks(
            context.user_data["student_number"],
            "all",  # Fetch all years
            context.user_data["department_id"],
        )

        if all_marks_data and all_marks_data["data"]:
            logger.info(
                f"Successfully fetched data: {len(all_marks_data['data'])} subjects"
            )
            logger.info("Proceeding with filtering...")
            # Store all marks data in context
            context.user_data["all_marks_data"] = all_marks_data

            # Filter data by academic year and specialization
            filtered_data = filter_marks_by_academic_year(
                all_marks_data, academic_year, specialization
            )

            if filtered_data and filtered_data["data"]:
                logger.info(f"Filtered subjects: {len(filtered_data['data'])}")
                # Pass the original all_marks_data to preserve student_name
                filtered_data["student_name"] = all_marks_data.get(
                    "student_name", "غير محدد"
                )
                await send_marks_result(
                    query, filtered_data, context.user_data, year_display
                )
            else:
                # Show proper message when no results found for the selected year
                logger.info("No results found for selected academic year")
                await query.edit_message_text(
                    f"❌ لم يتم العثور على نتائج للسنة المختارة: {year_display}\n\n"
                    f"🔍 الأسباب المحتملة:\n"
                    f"• لم تتقدم إلى أي مادة في هذه السنة\n"
                    f"• لم يتم رفع النتائج بعد\n"
                    f"• البيانات غير متاحة مؤقتاً\n\n"
                    f"💡 يمكنك:\n"
                    f"• اختيار سنة أخرى\n"
                    f"• التأكد من صحة رقمك الجامعي\n"
                    f"• المحاولة لاحقاً\n\n"
                    f"🔄 للبحث مرة أخرى، أرسل رقمك الجامعي."
                )
        else:
            logger.error("No data fetched from university website")
            await query.edit_message_text(
                "❌ لم يتم العثور على نتائج. تأكد من صحة البيانات.\n\n"
                "🔧 الأسباب المحتملة:\n"
                "• رقم الطالب غير صحيح\n"
                "• مشكلة في الاتصال بالموقع\n"
                "• الموقع غير متاح مؤقتاً\n\n"
                "🔄 حاول مرة أخرى بعد قليل."
            )

    except Exception as e:
        logger.error(f"Error fetching marks: {e}")
        await query.edit_message_text(
            "❌ حدث خطأ أثناء جلب النتائج.\n\n"
            "🔧 الأسباب المحتملة:\n"
            "• مشكلة في الاتصال بالإنترنت\n"
            "• الموقع غير متاح مؤقتاً\n"
            "• بيانات غير صحيحة\n\n"
            "🔄 حاول مرة أخرى بعد قليل."
        )


async def handle_year_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle year selection - now shows available years after fetching all data."""
    query = update.callback_query
    await query.answer()

    year_data = query.data.split("_")[1]

    # Get the marks data from context
    marks_data = context.user_data.get("all_marks_data")
    if not marks_data:
        await query.edit_message_text("❌ لم يتم العثور على البيانات. حاول مرة أخرى.")
        return

    # Filter data for selected year
    year_filtered_data = filter_marks_by_year(marks_data, year_data)

    if year_filtered_data:
        await send_marks_result(query, year_filtered_data, context.user_data, year_data)
    else:
        await query.edit_message_text(f"❌ لم يتم العثور على نتائج للسنة {year_data}.")


async def handle_department_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Handle department selection and fetch all years, then filter by academic year."""
    query = update.callback_query
    await query.answer()

    logger.info("handle_department_selection called")
    logger.info(f"User data: {context.user_data}")

    # Department is already set to "2" in handle_academic_year_selection
    dept_id = context.user_data.get("department_id", "2")
    logger.info(f"Using department_id: {dept_id}")

    # Show loading message
    await query.edit_message_text("⏳ جاري جلب النتائج...")

    try:
        # Fetch all years data
        logger.info(
            f"Fetching data for student: {context.user_data['student_number']}, department: {dept_id}"
        )
        all_marks_data = await fetch_student_marks(
            context.user_data["student_number"],
            "all",  # Fetch all years
            dept_id,
        )

        if all_marks_data and all_marks_data["data"]:
            logger.info(
                f"Successfully fetched data: {len(all_marks_data['data'])} subjects"
            )
            logger.info("Proceeding with filtering...")
            # Store all marks data in context
            context.user_data["all_marks_data"] = all_marks_data

            # Get academic year and specialization from context
            academic_year = context.user_data.get("academic_year")
            specialization = context.user_data.get("specialization")

            # Debug: Log the data we received
            logger.info(f"Total subjects fetched: {len(all_marks_data['data'])}")
            logger.info(
                f"Academic year: {academic_year}, Specialization: {specialization}"
            )

            # Filter data by academic year and specialization
            filtered_data = filter_marks_by_academic_year(
                all_marks_data, academic_year, specialization
            )

            if filtered_data and filtered_data["data"]:
                year_display = f"السنة {academic_year}"
                if specialization:
                    specialization_display = (
                        "حواسيب" if specialization == "computer" else "تحكم"
                    )
                    year_display += f" - {specialization_display}"

                logger.info(f"Filtered subjects: {len(filtered_data['data'])}")
                # Pass the original all_marks_data to preserve student_name
                filtered_data["student_name"] = all_marks_data.get(
                    "student_name", "غير محدد"
                )
                await send_marks_result(
                    query, filtered_data, context.user_data, year_display
                )
            else:
                year_display = f"السنة {academic_year}"
                if specialization:
                    specialization_display = (
                        "حواسيب" if specialization == "computer" else "تحكم"
                    )
                    year_display += f" - {specialization_display}"

                # Show proper message when no results found for the selected year
                logger.info("No results found for selected academic year")
                await query.edit_message_text(
                    f"❌ لم يتم العثور على نتائج للسنة المختارة: {year_display}\n\n"
                    f"🔍 الأسباب المحتملة:\n"
                    f"• لم تتقدم إلى أي مادة في هذه السنة\n"
                    f"• لم يتم رفع النتائج بعد\n"
                    f"• البيانات غير متاحة مؤقتاً\n\n"
                    f"💡 يمكنك:\n"
                    f"• اختيار سنة أخرى\n"
                    f"• التأكد من صحة رقمك الجامعي\n"
                    f"• المحاولة لاحقاً\n\n"
                    f"🔄 للبحث مرة أخرى، أرسل رقمك الجامعي."
                )
        else:
            logger.error("No data fetched from university website")
            await query.edit_message_text(
                "❌ لم يتم العثور على نتائج. تأكد من صحة البيانات.\n\n"
                "🔧 الأسباب المحتملة:\n"
                "• رقم الطالب غير صحيح\n"
                "• مشكلة في الاتصال بالموقع\n"
                "• الموقع غير متاح مؤقتاً\n\n"
                "🔄 حاول مرة أخرى بعد قليل."
            )

    except Exception as e:
        logger.error(f"Error fetching marks: {e}")
        await query.edit_message_text(
            "❌ حدث خطأ أثناء جلب النتائج.\n\n"
            "🔧 الأسباب المحتملة:\n"
            "• مشكلة في الاتصال بالإنترنت\n"
            "• الموقع غير متاح مؤقتاً\n"
            "• بيانات غير صحيحة\n\n"
            "🔄 حاول مرة أخرى بعد قليل."
        )


async def fetch_student_marks(student_number, year, department_id):
    """Fetch student marks from the university website."""
    logger.info(
        f"fetch_student_marks called with: student_number={student_number}, year={year}, department_id={department_id}"
    )
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Prepare payload based on year selection
            if year == "all":
                payload = {
                    "func": "14",
                    "set": "14",
                    "lang": "1",
                    "num": student_number,
                    "department_id": department_id,
                    "Year": "",
                    "Season": "-1",
                }
            else:
                year_mapping = {
                    "2025": "20252024",
                    "2024": "20242023",
                    "2023": "20232022",
                    "2022": "20222021",
                }
                payload = {
                    "func": "14",
                    "set": "14",
                    "lang": "1",
                    "num": student_number,
                    "department_id": department_id,
                    "Year": year_mapping.get(year, ""),
                    "Season": "1",
                }

            # Make request with session
            response = session.post(
                "https://www.damascusuniversity.edu.sy/fmee/index.php",
                data=payload,
                headers={
                    "Referer": "https://www.damascusuniversity.edu.sy/fmee/",
                },
                timeout=30,
                verify=False,  # Disable SSL verification for university site
            )

            if response.status_code != 200:
                if attempt < max_retries - 1:
                    continue
                return None

            # Parse HTML
            soup = BeautifulSoup(response.content, "html.parser")
            tables = soup.find_all("table")

            # Find table with marks
            marks_table = None
            student_info_table = None
            for table in tables:
                table_text = table.get_text()
                if "راسب" in table_text or "ناجح" in table_text:
                    marks_table = table
                elif "الرقم الجامعي" in table_text and "الأسم" in table_text:
                    student_info_table = table

            if not marks_table:
                if attempt < max_retries - 1:
                    continue
                return None

            # Extract student name from student info table
            student_name = "غير محدد"
            if student_info_table:
                info_rows = student_info_table.find_all("tr")
                if len(info_rows) > 1:
                    first_data_row = info_rows[1]
                    first_data_cells = first_data_row.find_all(["td", "th"])
                    if len(first_data_cells) >= 4:  # Name is in the 4th column
                        student_name = first_data_cells[3].get_text().strip()

            # Extract marks data
            rows = marks_table.find_all("tr")
            if len(rows) < 2:
                if attempt < max_retries - 1:
                    continue
                return None

            # Get header
            header_row = rows[0]
            header_cells = header_row.find_all(["td", "th"])
            headers = [cell.get_text().strip() for cell in header_cells]

            # Get data rows (all subjects, not just successful ones)
            data_rows = []
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) >= 6:  # Ensure we have enough columns
                    row_data = [cell.get_text().strip() for cell in cells]
                    data_rows.append(row_data)

            result = {
                "headers": headers,
                "data": data_rows,
                "total_subjects": len(data_rows),
                "student_name": student_name,
            }
            logger.info(f"fetch_student_marks returning: {len(data_rows)} subjects")
            return result

        except requests.exceptions.ConnectionError as e:
            logger.error(
                f"Connection error in fetch_student_marks (attempt {attempt + 1}): {e}"
            )
            if attempt < max_retries - 1:
                time.sleep(3)  # Wait 3 seconds before retry
                continue
            return None
        except requests.exceptions.Timeout as e:
            logger.error(
                f"Timeout error in fetch_student_marks (attempt {attempt + 1}): {e}"
            )
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait 2 seconds before retry
                continue
            return None
        except Exception as e:
            logger.error(f"Error in fetch_student_marks (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait 2 seconds before retry
                continue
            return None

    logger.error("fetch_student_marks failed after all retries")
    return None


def get_available_years(marks_data):
    """Extract available years from marks data."""
    logger.info("get_available_years called")
    years = set()
    for row in marks_data["data"]:
        if len(row) >= 2:  # Make sure we have year column
            year_text = row[1]  # Year column
            # Extract year from format like "2025-2024"
            if "-" in year_text:
                year = year_text.split("-")[0]
                years.add(year)
    result = sorted(list(years), reverse=True)  # Latest first
    logger.info(f"get_available_years returning: {result}")
    return result


def detect_student_specialization(marks_data):
    """Detect student's actual specialization based on their subjects."""
    if not marks_data or not marks_data["data"]:
        return None

    # Get all subjects from student's data
    student_subjects = set()
    for row in marks_data["data"]:
        if len(row) >= 6:
            subject = row[0]
            student_subjects.add(subject)

    # Define computer-specific subjects (only unique to computer specialization)
    computer_subjects = {
        "النظم المضمنة",
        "شبكات حاسوبية متقدمة",
        "برمجة الشبكات الحاسوبية",
        "أمن المعلومات والشبكات",
        "شبكات الحواسيب وتراسل المعطيات",
        "نظم الاتصالات الحديثة",
        "نظرية الترميز",
    }

    # Define control-specific subjects (only unique to control specialization)
    control_subjects = {
        "التحكم اللاخطي",
        "التحكم العائم",
        "الآلات الكهربائية الخاصة",
        "الالكترونيات الصناعية",
        "النظم الخبيرة",
        "نظم الروبوتية والآلات المبرمجة",
        "شبكات الحواسيب و تراسل المعطيات",
        "الشبكات الحاسوبية الصناعية وبروتوكولاتها",
    }

    # Define shared subjects (common to both specializations)
    shared_subjects = {
        "نظم التشغيل",
        "الاتصالات الرقمية",
        "الذكاء الصنعي",
        "قواعد البيانات",
        "البنى المتقدمة للحاسوب",
        "معالجة الاشارة",
        "الوحدات المحيطية للحاسوب",
        "هندسة البرمجيات",
    }

    # Count matches for each specialization
    computer_matches = 0
    control_matches = 0
    shared_matches = 0

    for subject in student_subjects:
        # Check for computer-specific subjects
        for comp_subject in computer_subjects:
            if comp_subject in subject or subject in comp_subject:
                computer_matches += 1
                break
        else:
            # Check for control-specific subjects
            for ctrl_subject in control_subjects:
                if ctrl_subject in subject or subject in ctrl_subject:
                    control_matches += 1
                    break
            else:
                # Check for shared subjects
                for shared_subject in shared_subjects:
                    if shared_subject in subject or subject in shared_subject:
                        shared_matches += 1
                        break

    # Determine specialization based on matches
    # If only shared subjects, cannot determine specialization
    if computer_matches == 0 and control_matches == 0 and shared_matches > 0:
        return None

    # If only computer-specific subjects or more computer matches
    if computer_matches > control_matches and computer_matches > 0:
        return "computer"
    # If only control-specific subjects or more control matches
    elif control_matches > computer_matches and control_matches > 0:
        return "control"
    # If equal matches or no specific subjects
    else:
        return None


def get_missing_subjects(marks_data, academic_year, specialization=None):
    """Get subjects that should be in this academic year but are not found."""
    if not marks_data or not marks_data["data"]:
        return []

    # Define subjects for each academic year based on subjects.txt
    academic_year_subjects = {
        "1": [
            "اللغة الاجنبية (1)",
            "اللغة الاجنبية (2)",
            "التحليل الرياضي (1)",
            "التحليل الرياضي (2)",
            "الفيزياء (1)",
            "الفيزياء (2)",
            "أسس الهندسة الكهربائية",
            "الجبر الخطي",
            "الميكانيك الهندسي",
            "اللغة العربية",
            "البرمجة (1)",
            "المدخل الى الحاسوب والبرمجة",
            "الثقافة القومية",
            "الورشات التخصصية (كهربائية والكترونية)",
        ],
        "2": [
            "الدارات المنطقية",
            "الرياضيات المتقطعة",
            "الدارات الكهربائية (1)",
            "الحقول الكهرطيسية",
            "أسس الهندسة الالكترونية",
            "الخوارزميات وبنى المعطيات",
            "اللغة الاجنبية (3)",
            "التمثيل والرسم الهندسي",
            "التحليل الرياضي (3)",
            "البرمجة (2)",
            "التحليل العددي",
            "اللغة الاجنبية (4)",
            "القياسات وأجهزة القياس الكهربائية",
            "الدارات الكهربائية (2)",
        ],
        "3": [
            "تحليل النظم",
            "نظم التحكم الآلي",
            "نظرية التحكم الآلي",
            "المعالجات الصغرية ونظمها",
            "الدارات الالكترونية (1)",
            "القياسات الالكترونية",
            "أسس هندسة الاتصالات",
            "الدارات الالكترونية (2)",
            "بنية الحاسوب وتنظيمه",
            "النظم المنطقية والرقمية",
            "الاحتمال والاحصاء",
            "بحوث العمليات",
        ],
        "4_computer": [
            "قواعد البيانات",
            "الاتصالات الرقمية",
            "الذكاء الصنعي",
            "نظم التشغيل",
            "معالجة الاشارة",
            "نظرية الترميز",
            "الوحدات المحيطية للحاسوب",
            "البنى المتقدمة للحاسوب",
            "هندسة البرمجيات",
            "النظم المضمنة",
            "شبكات الحواسيب وتراسل المعطيات",
        ],
        "4_control": [
            "نظم التشغيل",
            "التحكم اللاخطي",
            "الاتصالات الرقمية",
            "الالكترونيات الصناعية",
            "التحكم العائم",
            "الآلات الكهربائية الخاصة",
            "الذكاء الصنعي",
            "قواعد البيانات",
            "الوحدات المحيطية للحاسوب",
            "شبكات الحواسيب و تراسل المعطيات",
            "هندسة البرمجيات",
            "معالجة الاشارة",
        ],
        "5_computer": [
            "الابصار الحاسوبي",
            "شبكات حاسوبية متقدمة",
            "الوثوقية ومعايير الجودة",
            "الشبكات العصبونية",
            "نظم الاتصالات الحديثة",
            "برمجة الشبكات الحاسوبية",
            "الاقتصاد الهندسي وادارة الاعمال",
            "أمن المعلومات والشبكات",
        ],
        "5_control": [
            "النظم الخبيرة",
            "الوثوقية ومعايير الجودة",
            "الابصار الحاسوبي",
            "الاقتصاد الهندسي وادارة الاعمال",
            "الشبكات العصبونية",
            "نظم الروبوتية والآلات المبرمجة",
            "الشبكات الحاسوبية الصناعية وبروتوكولاتها",
            "البنى المتقدمة للحاسوب",
        ],
    }

    # Get target subjects for the academic year
    year_key = academic_year
    if specialization:
        year_key = f"{academic_year}_{specialization}"

    target_subjects = academic_year_subjects.get(year_key, [])
    if not target_subjects:
        return []

    # Get subjects that are actually found
    found_subjects = set()
    for row in marks_data["data"]:
        if len(row) >= 6:
            subject = row[0]
            found_subjects.add(subject)

    # Find missing subjects
    missing_subjects = []
    for target_subject in target_subjects:
        found = False
        for found_subject in found_subjects:
            if (
                target_subject == found_subject
                or target_subject in found_subject
                or found_subject in target_subject
            ):
                found = True
                break
        if not found:
            missing_subjects.append(target_subject)

    return missing_subjects


def filter_marks_by_academic_year(marks_data, academic_year, specialization=None):
    """Filter marks data by academic year and specialization."""
    logger.info(
        f"filter_marks_by_academic_year called with academic_year={academic_year}, specialization={specialization}"
    )
    if not marks_data or not marks_data["data"]:
        logger.info("No marks data provided")
        return None

    # Define subjects for each academic year based on subjects.txt
    academic_year_subjects = {
        "1": [
            "اللغة الاجنبية (1)",
            "اللغة الاجنبية (2)",
            "التحليل الرياضي (1)",
            "التحليل الرياضي (2)",
            "الفيزياء (1)",
            "الفيزياء (2)",
            "أسس الهندسة الكهربائية",
            "الجبر الخطي",
            "الميكانيك الهندسي",
            "اللغة العربية",
            "البرمجة (1)",
            "المدخل الى الحاسوب والبرمجة",
            "الثقافة القومية",
            "الورشات التخصصية (كهربائية والكترونية)",
        ],
        "2": [
            "الدارات المنطقية",
            "الرياضيات المتقطعة",
            "الدارات الكهربائية (1)",
            "الحقول الكهرطيسية",
            "أسس الهندسة الالكترونية",
            "الخوارزميات وبنى المعطيات",
            "اللغة الاجنبية (3)",
            "التمثيل والرسم الهندسي",
            "التحليل الرياضي (3)",
            "البرمجة (2)",
            "التحليل العددي",
            "اللغة الاجنبية (4)",
            "القياسات وأجهزة القياس الكهربائية",
            "الدارات الكهربائية (2)",
        ],
        "3": [
            "تحليل النظم",
            "نظم التحكم الآلي",
            "نظرية التحكم الآلي",
            "المعالجات الصغرية ونظمها",
            "الدارات الالكترونية (1)",
            "القياسات الالكترونية",
            "أسس هندسة الاتصالات",
            "الدارات الالكترونية (2)",
            "بنية الحاسوب وتنظيمه",
            "النظم المنطقية والرقمية",
            "الاحتمال والاحصاء",
            "بحوث العمليات",
        ],
        "4_computer": [
            "قواعد البيانات",
            "الاتصالات الرقمية",
            "الذكاء الصنعي",
            "نظم التشغيل",
            "معالجة الاشارة",
            "نظرية الترميز",
            "الوحدات المحيطية للحاسوب",
            "البنى المتقدمة للحاسوب",
            "هندسة البرمجيات",
            "النظم المضمنة",
            "شبكات الحواسيب وتراسل المعطيات",
        ],
        "4_control": [
            "نظم التشغيل",
            "التحكم اللاخطي",
            "الاتصالات الرقمية",
            "الالكترونيات الصناعية",
            "التحكم العائم",
            "الآلات الكهربائية الخاصة",
            "الذكاء الصنعي",
            "قواعد البيانات",
            "الوحدات المحيطية للحاسوب",
            "شبكات الحواسيب و تراسل المعطيات",
            "هندسة البرمجيات",
            "معالجة الاشارة",
        ],
        "5_computer": [
            "الابصار الحاسوبي",
            "شبكات حاسوبية متقدمة",
            "الوثوقية ومعايير الجودة",
            "الشبكات العصبونية",
            "نظم الاتصالات الحديثة",
            "برمجة الشبكات الحاسوبية",
            "الاقتصاد الهندسي وادارة الاعمال",
            "أمن المعلومات والشبكات",
        ],
        "5_control": [
            "النظم الخبيرة",
            "الوثوقية ومعايير الجودة",
            "الابصار الحاسوبي",
            "الاقتصاد الهندسي وادارة الاعمال",
            "الشبكات العصبونية",
            "نظم الروبوتية والآلات المبرمجة",
            "الشبكات الحاسوبية الصناعية وبروتوكولاتها",
            "البنى المتقدمة للحاسوب",
        ],
    }

    # Get subjects for the selected academic year
    if specialization:
        year_key = f"{academic_year}_{specialization}"
        target_subjects = academic_year_subjects.get(year_key, [])
    else:
        # For years 4 and 5 without specialization, get all subjects from both specializations
        if academic_year in ["4", "5"]:
            computer_key = f"{academic_year}_computer"
            control_key = f"{academic_year}_control"
            computer_subjects = academic_year_subjects.get(computer_key, [])
            control_subjects = academic_year_subjects.get(control_key, [])
            # Combine both lists and remove duplicates
            target_subjects = list(set(computer_subjects + control_subjects))
        else:
            year_key = academic_year
            target_subjects = academic_year_subjects.get(year_key, [])

    # Debug logging
    logger.info(f"Academic year: {academic_year}, Specialization: {specialization}")
    if specialization:
        logger.info(f"Year key: {academic_year}_{specialization}")
    else:
        logger.info(f"Year key: {academic_year} (no specialization)")
    logger.info(f"Target subjects count: {len(target_subjects)}")

    if not target_subjects:
        return None

    # Filter data to include only subjects from the academic year
    filtered_data = []
    logger.info(f"Looking for subjects in academic year {academic_year}")
    logger.info(f"Target subjects: {target_subjects[:3]}...")  # Show first 3
    logger.info(f"Total subjects to search: {len(marks_data['data'])}")

    for row in marks_data["data"]:
        if len(row) >= 6:
            subject = row[0]  # Subject name
            final_mark = row[5] if len(row) > 5 else ""
            result = row[6] if len(row) > 6 else ""

            # Skip subjects without results or marks
            if (
                not final_mark
                or final_mark.strip() == ""
                or not result
                or result.strip() == ""
            ):
                continue

            # Check if subject matches any of the target subjects (partial match)
            for target_subject in target_subjects:
                # More precise matching - exact match or very close match
                if (
                    subject == target_subject
                    or target_subject in subject
                    or subject in target_subject
                ):
                    filtered_data.append(row)
                    logger.info(f"Matched: {subject} -> {target_subject}")
                    break

    logger.info(f"Found {len(filtered_data)} matching subjects")

    if not filtered_data:
        logger.info("No filtered data found for the selected academic year")
        # Return None to indicate no results found for this academic year
        return None

    # Group by subject and get latest mark for each
    subjects = {}
    for row in filtered_data:
        if len(row) >= 6:
            subject = row[0]  # Subject name
            year = row[1] if len(row) > 1 else ""  # Year
            semester = row[2] if len(row) > 2 else ""  # Semester
            final_mark = row[5] if len(row) > 5 else ""
            result = row[6] if len(row) > 6 else ""

            # Skip if no valid mark or result
            if (
                not final_mark
                or final_mark.strip() == ""
                or not result
                or result.strip() == ""
            ):
                continue

            # Keep only the latest attempt for each subject
            if subject not in subjects:
                subjects[subject] = row
            else:
                # Compare years first (higher year is more recent)
                current_year = subjects[subject][1]
                if year > current_year:
                    subjects[subject] = row
                elif year == current_year:
                    # If same year, compare semesters (فصل ثاني is later than فصل أول)
                    current_semester = subjects[subject][2]
                    if semester == "فصل ثاني" and current_semester == "فصل أول":
                        subjects[subject] = row
                    # If same year and semester, keep the one with higher mark
                    elif semester == current_semester:
                        try:
                            current_mark = float(subjects[subject][5])
                            new_mark = float(row[5])
                            if new_mark > current_mark:
                                subjects[subject] = row
                        except (ValueError, IndexError):
                            pass

    # Convert back to list format
    final_data = list(subjects.values())

    return {
        "headers": marks_data["headers"],
        "data": final_data,
        "total_subjects": len(final_data),
    }


def filter_marks_by_year(marks_data, selected_year):
    """Filter marks data by selected year and get latest mark for each subject."""
    if not marks_data or not marks_data["data"]:
        return None

    # Filter data for selected year
    year_data = []
    for row in marks_data["data"]:
        if len(row) >= 6 and selected_year in row[1]:  # Check year column
            final_mark = row[5] if len(row) > 5 else ""
            result = row[6] if len(row) > 6 else ""

            # Skip subjects without results or marks
            if (
                not final_mark
                or final_mark.strip() == ""
                or not result
                or result.strip() == ""
            ):
                continue

            year_data.append(row)

    if not year_data:
        return None

    # Group by subject and get latest mark for each
    subjects = {}
    for row in year_data:
        if len(row) >= 6:
            subject = row[0]  # Subject name
            semester = row[2]  # Semester
            final_mark = row[5] if len(row) > 5 else ""
            result = row[6] if len(row) > 6 else ""

            # Skip if no valid mark or result
            if (
                not final_mark
                or final_mark.strip() == ""
                or not result
                or result.strip() == ""
            ):
                continue

            # Keep only the latest semester for each subject
            if subject not in subjects:
                subjects[subject] = row
            else:
                # Compare semesters (فصل ثاني is later than فصل أول)
                current_semester = subjects[subject][2]
                if semester == "فصل ثاني" and current_semester == "فصل أول":
                    subjects[subject] = row
                # If same semester, keep the one with higher mark
                elif semester == current_semester:
                    try:
                        current_mark = float(subjects[subject][5])
                        new_mark = float(row[5])
                        if new_mark > current_mark:
                            subjects[subject] = row
                    except (ValueError, IndexError):
                        pass

    # Convert back to list format
    filtered_data = list(subjects.values())

    result = {
        "headers": marks_data["headers"],
        "data": filtered_data,
        "total_subjects": len(filtered_data),
    }
    logger.info(
        f"filter_marks_by_academic_year returning {len(filtered_data)} subjects"
    )
    return result


async def send_marks_result(query, marks_data, user_data, selected_year=None):
    """Send formatted marks result to user."""
    logger.info(f"send_marks_result called with {len(marks_data['data'])} subjects")
    try:
        # Calculate statistics (only for successful subjects)
        total_marks = 0
        valid_marks = 0
        successful_subjects = 0
        failed_subjects = 0

        for row in marks_data["data"]:
            if len(row) >= 6:  # Ensure we have the final mark column
                try:
                    mark = float(row[5])  # Final mark column
                    result = row[6] if len(row) > 6 else ""  # Result column

                    if "ناجح" in result:
                        total_marks += mark
                        valid_marks += 1
                        successful_subjects += 1
                    else:
                        failed_subjects += 1
                except (ValueError, IndexError):
                    pass

        average = total_marks / valid_marks if valid_marks > 0 else 0

        # Get missing subjects
        missing_subjects = get_missing_subjects(
            marks_data, user_data.get("academic_year"), user_data.get("specialization")
        )

        # Format result message
        year_display = selected_year if selected_year else "جميع السنوات"

        # Add specialization info if selected
        specialization_info = ""
        specialization = user_data.get("specialization")
        if specialization:
            specialization_display = (
                "حواسيب" if specialization == "computer" else "تحكم"
            )
            specialization_info = f"\n🎯 التخصص: {specialization_display}"

        # Get student name from marks data
        student_name = marks_data.get("student_name", "غير محدد")

        result_text = f"""🎓 نتائج الطالب: {user_data['student_number']}
👤 الاسم: {student_name}
📚 القسم: {DEPARTMENTS.get(user_data['department_id'], 'غير محدد')}
📅 السنة: {year_display}{specialization_info}

📊 الإحصائيات:
• إجمالي المواد: {marks_data['total_subjects']}
• المواد الناجحة: {successful_subjects}
• المواد الراسبة: {failed_subjects}
• المعدل النهائي: {average:.2f}

📋 النتائج:"""

        # Add all marks details
        for i, row in enumerate(marks_data["data"]):
            if len(row) >= 6:
                subject = row[0] if len(row) > 0 else "غير محدد"
                final_mark = row[5] if len(row) > 5 else "غير محدد"
                semester = row[2] if len(row) > 2 else "غير محدد"
                result = row[6] if len(row) > 6 else "غير محدد"
                year = row[1] if len(row) > 1 else "غير محدد"

                # Truncate long subject names
                if len(subject) > 35:
                    subject = subject[:32] + "..."

                # Add status emoji
                status_emoji = "✅" if "ناجح" in result else "❌"

                result_text += (
                    f"\n{status_emoji} {subject}: {final_mark} ({year} - {semester})"
                )

        # Add missing subjects if any
        if missing_subjects:
            result_text += "\n\n❌ المواد التي لم يتم التقدم إليها:"
            for missing_subject in missing_subjects:
                result_text += f"\n• {missing_subject}"

        await query.edit_message_text(result_text)

    except Exception as e:
        logger.error(f"Error in send_marks_result: {e}")
        await query.edit_message_text("❌ حدث خطأ في عرض النتائج.")


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries."""
    query = update.callback_query

    logger.info(f"handle_callback_query called with data: {query.data}")

    if query.data.startswith("academic_year_"):
        await handle_academic_year_selection(update, context)
    elif query.data == "new_search":
        await query.edit_message_text("📝 أرسل رقمك الجامعي للحصول على النتائج:")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    error = context.error

    # Don't notify users about Conflict errors (internal issue)
    if isinstance(error, Conflict):
        logger.warning(f"Conflict error (another instance may be running): {error}")
        return

    logger.error(f"Exception while handling an update: {error}", exc_info=error)

    # Only log errors, don't crash the bot
    if update and isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."
            )
        except Exception as e:
            logger.error(f"Error sending error message: {e}")


def create_application():
    """Create and configure the bot application."""
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("get_marks", get_marks_command))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_student_number)
    )

    # Add error handler
    application.add_error_handler(error_handler)

    return application


def run_bot_with_retry():
    """Run the bot with automatic reconnection on errors."""
    max_retries = float("inf")  # Retry forever
    retry_delay = 5  # Start with 5 seconds delay

    retry_count = 0
    application = None

    while retry_count < max_retries:
        try:
            logger.info(f"🤖 Bot is starting... (Attempt {retry_count + 1})")
            print(f"🤖 Bot is starting... (Attempt {retry_count + 1})")

            # Clean up previous application if it exists
            if application is not None:
                try:
                    logger.info("Cleaning up previous application instance...")
                    application.stop()
                    application.shutdown()
                    time.sleep(2)  # Wait for cleanup
                except Exception as cleanup_error:
                    logger.warning(f"Error during cleanup: {cleanup_error}")

            application = create_application()

            logger.info("✅ Bot is running and polling for updates...")
            print("✅ Bot is running and polling for updates...")

            # Reset retry delay on successful start
            retry_delay = 5
            retry_count = 0

            # Start polling - this will block until stopped or error
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,  # Drop pending updates to avoid conflicts
                close_loop=False,
            )

        except KeyboardInterrupt:
            logger.info("🛑 Bot stopped by user (KeyboardInterrupt)")
            print("🛑 Bot stopped by user")
            if application:
                try:
                    application.stop()
                    application.shutdown()
                except Exception:
                    pass
            break

        except Conflict as e:
            # Conflict error means another instance is running
            retry_count += 1
            error_msg = (
                f"⚠️ Conflict detected: Another bot instance may be running. {str(e)}"
            )
            logger.warning(error_msg)
            print(error_msg)
            print("💡 Make sure only one instance of the bot is running.")
            print(f"🔄 Waiting {retry_delay} seconds before retry...")

            # Clean up this instance
            if application:
                try:
                    application.stop()
                    application.shutdown()
                    time.sleep(2)
                except Exception:
                    pass
                application = None

            # Longer wait for conflict errors (30 seconds minimum)
            time.sleep(max(retry_delay, 30))
            retry_delay = min(retry_delay * 2, 120)  # Max 2 minutes for conflicts

        except (TimedOut, NetworkError) as e:
            # Network errors - retry quickly
            retry_count += 1
            error_msg = f"🌐 Network error: {type(e).__name__}: {str(e)}"
            logger.warning(error_msg)
            print(error_msg)
            print(f"🔄 Reconnecting in {retry_delay} seconds...")

            if application:
                try:
                    application.stop()
                    application.shutdown()
                except Exception:
                    pass
                application = None

            time.sleep(retry_delay)
            retry_delay = min(
                retry_delay * 1.5, 30
            )  # Max 30 seconds for network errors

        except Exception as e:
            retry_count += 1
            error_msg = f"❌ Error occurred: {type(e).__name__}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            print(error_msg)
            print(f"🔄 Reconnecting in {retry_delay} seconds...")

            # Clean up on any error
            if application:
                try:
                    application.stop()
                    application.shutdown()
                except Exception:
                    pass
                application = None

            # Exponential backoff with max delay of 60 seconds
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)


def run_flask():
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting Flask (waitress) server on port {port}")
    serve(app, host="0.0.0.0", port=port)


def main():
    """Main entry point for the bot and Flask app."""
    logger.info("=" * 50)
    logger.info(f"Bot startup at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)

    try:
        # Run Flask (health check) in a background thread
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()

        # Run the bot in the main thread
        run_bot_with_retry()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
        print("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
