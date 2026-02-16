import logging
import os
import re
import sys
import time
from datetime import datetime

import requests
import urllib3
from dotenv import load_dotenv
from flask import Flask, jsonify, request

# Load environment variables
load_dotenv()

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

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

# Subjects for each academic year
ACADEMIC_YEAR_SUBJECTS = {
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


# ─── Core logic ───────────────────────────────────────────────────────────────


def fetch_student_marks(student_number, year, department_id):
    """Fetch student marks from the university website."""
    logger.info(
        f"fetch_student_marks called with: student_number={student_number}, year={year}, department_id={department_id}"
    )
    max_retries = 3
    for attempt in range(max_retries):
        try:
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

            response = session.post(
                "https://www.damascusuniversity.edu.sy/fmee/index.php",
                data=payload,
                headers={
                    "Referer": "https://www.damascusuniversity.edu.sy/fmee/",
                },
                timeout=30,
                verify=False,
            )

            if response.status_code != 200:
                if attempt < max_retries - 1:
                    continue
                return None

            soup = BeautifulSoup(response.content, "html.parser")
            tables = soup.find_all("table")

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

            student_name = "غير محدد"
            if student_info_table:
                info_rows = student_info_table.find_all("tr")
                if len(info_rows) > 1:
                    first_data_row = info_rows[1]
                    first_data_cells = first_data_row.find_all(["td", "th"])
                    if len(first_data_cells) >= 4:
                        student_name = first_data_cells[3].get_text().strip()

            rows = marks_table.find_all("tr")
            if len(rows) < 2:
                if attempt < max_retries - 1:
                    continue
                return None

            header_row = rows[0]
            header_cells = header_row.find_all(["td", "th"])
            headers = [cell.get_text().strip() for cell in header_cells]

            data_rows = []
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) >= 6:
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
            logger.error(f"Connection error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
                continue
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return None
        except Exception as e:
            logger.error(f"Error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return None

    logger.error("fetch_student_marks failed after all retries")
    return None


def filter_marks_by_academic_year(marks_data, academic_year, specialization=None):
    """Filter marks data by academic year and specialization."""
    logger.info(
        f"filter_marks_by_academic_year called with academic_year={academic_year}, specialization={specialization}"
    )
    if not marks_data or not marks_data["data"]:
        return None

    if specialization:
        year_key = f"{academic_year}_{specialization}"
        target_subjects = ACADEMIC_YEAR_SUBJECTS.get(year_key, [])
    else:
        if academic_year in ["4", "5"]:
            computer_key = f"{academic_year}_computer"
            control_key = f"{academic_year}_control"
            computer_subjects = ACADEMIC_YEAR_SUBJECTS.get(computer_key, [])
            control_subjects = ACADEMIC_YEAR_SUBJECTS.get(control_key, [])
            target_subjects = list(set(computer_subjects + control_subjects))
        else:
            target_subjects = ACADEMIC_YEAR_SUBJECTS.get(academic_year, [])

    logger.info(f"Target subjects count: {len(target_subjects)}")
    if not target_subjects:
        return None

    filtered_data = []
    for row in marks_data["data"]:
        if len(row) >= 6:
            subject = row[0]
            final_mark = row[5] if len(row) > 5 else ""
            result = row[6] if len(row) > 6 else ""

            if (
                not final_mark
                or final_mark.strip() == ""
                or not result
                or result.strip() == ""
            ):
                continue

            for target_subject in target_subjects:
                if (
                    subject == target_subject
                    or target_subject in subject
                    or subject in target_subject
                ):
                    filtered_data.append(row)
                    break

    logger.info(f"Found {len(filtered_data)} matching subjects")
    if not filtered_data:
        return None

    # Keep latest attempt per subject
    subjects = {}
    for row in filtered_data:
        if len(row) >= 6:
            subject = row[0]
            year = row[1] if len(row) > 1 else ""
            semester = row[2] if len(row) > 2 else ""
            final_mark = row[5] if len(row) > 5 else ""
            result = row[6] if len(row) > 6 else ""

            if (
                not final_mark
                or final_mark.strip() == ""
                or not result
                or result.strip() == ""
            ):
                continue

            if subject not in subjects:
                subjects[subject] = row
            else:
                current_year = subjects[subject][1]
                if year > current_year:
                    subjects[subject] = row
                elif year == current_year:
                    current_semester = subjects[subject][2]
                    if semester == "فصل ثاني" and current_semester == "فصل أول":
                        subjects[subject] = row
                    elif semester == current_semester:
                        try:
                            current_mark = float(subjects[subject][5])
                            new_mark = float(row[5])
                            if new_mark > current_mark:
                                subjects[subject] = row
                        except (ValueError, IndexError):
                            pass

    final_data = list(subjects.values())
    return {
        "headers": marks_data["headers"],
        "data": final_data,
        "total_subjects": len(final_data),
    }


def get_missing_subjects(marks_data, academic_year, specialization=None):
    """Get subjects that should be in this academic year but are not found."""
    if not marks_data or not marks_data["data"]:
        return []

    year_key = academic_year
    if specialization:
        year_key = f"{academic_year}_{specialization}"

    target_subjects = ACADEMIC_YEAR_SUBJECTS.get(year_key, [])
    if not target_subjects:
        return []

    found_subjects = set()
    for row in marks_data["data"]:
        if len(row) >= 6:
            found_subjects.add(row[0])

    missing = []
    for target in target_subjects:
        found = False
        for fs in found_subjects:
            if target == fs or target in fs or fs in target:
                found = True
                break
        if not found:
            missing.append(target)
    return missing


def compute_statistics(marks_data):
    """Compute statistics from marks data."""
    total_marks = 0
    valid_marks = 0
    successful = 0
    failed = 0

    for row in marks_data["data"]:
        if len(row) >= 6:
            try:
                mark = float(row[5])
                result = row[6] if len(row) > 6 else ""
                if "ناجح" in result:
                    total_marks += mark
                    valid_marks += 1
                    successful += 1
                else:
                    failed += 1
            except (ValueError, IndexError):
                pass

    average = total_marks / valid_marks if valid_marks > 0 else 0
    return {
        "total_subjects": marks_data["total_subjects"],
        "successful_subjects": successful,
        "failed_subjects": failed,
        "average": round(average, 2),
    }


def format_marks_text(
    marks_data,
    student_number,
    department_id,
    year_display,
    specialization,
    student_name,
):
    """Format marks into a Telegram-friendly text message."""
    stats = compute_statistics(marks_data)
    missing_subjects = get_missing_subjects(
        marks_data,
        # extract numeric year from year_display
        (
            year_display.replace("السنة ", "").split(" ")[0]
            if "السنة" in year_display
            else year_display
        ),
        specialization,
    )

    specialization_info = ""
    if specialization:
        specialization_display = "حواسيب" if specialization == "computer" else "تحكم"
        specialization_info = f"\n🎯 التخصص: {specialization_display}"

    text = f"""🎓 نتائج الطالب: {student_number}
👤 الاسم: {student_name}
📚 القسم: {DEPARTMENTS.get(department_id, 'غير محدد')}
📅 السنة: {year_display}{specialization_info}

📊 الإحصائيات:
• إجمالي المواد: {stats['total_subjects']}
• المواد الناجحة: {stats['successful_subjects']}
• المواد الراسبة: {stats['failed_subjects']}
• المعدل النهائي: {stats['average']:.2f}

📋 النتائج:"""

    for row in marks_data["data"]:
        if len(row) >= 6:
            subject = row[0] if len(row) > 0 else "غير محدد"
            final_mark = row[5] if len(row) > 5 else "غير محدد"
            semester = row[2] if len(row) > 2 else "غير محدد"
            result = row[6] if len(row) > 6 else "غير محدد"
            year = row[1] if len(row) > 1 else "غير محدد"

            if len(subject) > 35:
                subject = subject[:32] + "..."

            status_emoji = "✅" if "ناجح" in result else "❌"
            text += f"\n{status_emoji} {subject}: {final_mark} ({year} - {semester})"

    if missing_subjects:
        text += "\n\n❌ المواد التي لم يتم التقدم إليها:"
        for ms in missing_subjects:
            text += f"\n• {ms}"

    return text


# ─── API Routes ───────────────────────────────────────────────────────────────


@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "running", "message": "DU FMEE Results API ✅"}), 200


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200


@app.route("/api/departments", methods=["GET"])
def list_departments():
    """Return available departments."""
    return jsonify({"departments": DEPARTMENTS}), 200


@app.route("/api/academic_years", methods=["GET"])
def list_academic_years():
    """Return available academic year choices."""
    years = [
        {"key": "1", "label": "السنة الأولى"},
        {"key": "2", "label": "السنة الثانية"},
        {"key": "3", "label": "السنة الثالثة"},
        {
            "key": "4_computer",
            "label": "السنة الرابعة - حواسيب",
            "academic_year": "4",
            "specialization": "computer",
        },
        {
            "key": "4_control",
            "label": "السنة الرابعة - تحكم",
            "academic_year": "4",
            "specialization": "control",
        },
        {
            "key": "5_computer",
            "label": "السنة الخامسة - حواسيب",
            "academic_year": "5",
            "specialization": "computer",
        },
        {
            "key": "5_control",
            "label": "السنة الخامسة - تحكم",
            "academic_year": "5",
            "specialization": "control",
        },
    ]
    return jsonify({"academic_years": years}), 200


@app.route("/api/get_marks", methods=["POST"])
def get_marks():
    """
    Main endpoint – fetches and filters student marks.

    Expected JSON body:
    {
        "student_number": "1234567890",
        "academic_year": "3",              // "1"-"5"
        "specialization": null,            // null, "computer", or "control"
        "department_id": "2"               // optional, defaults to "2"
    }

    Returns JSON with:
    - formatted_text: ready-to-send Telegram message
    - statistics: dict with totals/average
    - subjects: list of subject detail dicts
    - missing_subjects: list of not-taken subjects
    - student_name: name from university site
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body is required"}), 400

    student_number = str(data.get("student_number", "")).strip()
    academic_year = str(data.get("academic_year", "")).strip()
    specialization = data.get("specialization")  # null / "computer" / "control"
    department_id = str(data.get("department_id", "2")).strip()

    # Validate student number
    if not re.match(r"^\d{10}$", student_number):
        return jsonify({"error": "رقم جامعي غير صحيح. يجب أن يكون 10 أرقام."}), 400

    # Validate academic year
    if academic_year not in ["1", "2", "3", "4", "5"]:
        return (
            jsonify({"error": "السنة الدراسية غير صحيحة. يجب أن تكون بين 1 و 5."}),
            400,
        )

    # Validate specialization for years 4 and 5
    if academic_year in ["4", "5"] and specialization not in [
        None,
        "computer",
        "control",
    ]:
        return (
            jsonify(
                {"error": "التخصص غير صحيح. يجب أن يكون computer أو control أو فارغ."}
            ),
            400,
        )

    logger.info(
        f"API get_marks: student={student_number}, year={academic_year}, "
        f"spec={specialization}, dept={department_id}"
    )

    # Build year display
    year_display = f"السنة {academic_year}"
    if specialization:
        spec_display = "حواسيب" if specialization == "computer" else "تحكم"
        year_display += f" - {spec_display}"

    try:
        # Fetch all marks
        all_marks_data = fetch_student_marks(student_number, "all", department_id)

        if not all_marks_data or not all_marks_data["data"]:
            return (
                jsonify(
                    {
                        "error": "لم يتم العثور على نتائج. تأكد من صحة البيانات.",
                        "formatted_text": (
                            "❌ لم يتم العثور على نتائج. تأكد من صحة البيانات.\n\n"
                            "🔧 الأسباب المحتملة:\n"
                            "• رقم الطالب غير صحيح\n"
                            "• مشكلة في الاتصال بالموقع\n"
                            "• الموقع غير متاح مؤقتاً\n\n"
                            "🔄 حاول مرة أخرى بعد قليل."
                        ),
                    }
                ),
                404,
            )

        student_name = all_marks_data.get("student_name", "غير محدد")

        # Filter by academic year
        filtered_data = filter_marks_by_academic_year(
            all_marks_data, academic_year, specialization
        )

        if not filtered_data or not filtered_data["data"]:
            return (
                jsonify(
                    {
                        "error": f"لم يتم العثور على نتائج للسنة المختارة: {year_display}",
                        "student_name": student_name,
                        "formatted_text": (
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
                        ),
                    }
                ),
                404,
            )

        filtered_data["student_name"] = student_name

        # Compute statistics
        stats = compute_statistics(filtered_data)
        missing = get_missing_subjects(filtered_data, academic_year, specialization)

        # Build subject list
        subjects_list = []
        for row in filtered_data["data"]:
            if len(row) >= 6:
                result_str = row[6] if len(row) > 6 else ""
                subjects_list.append(
                    {
                        "subject": row[0],
                        "year": row[1] if len(row) > 1 else "",
                        "semester": row[2] if len(row) > 2 else "",
                        "practical_mark": row[3] if len(row) > 3 else "",
                        "theory_mark": row[4] if len(row) > 4 else "",
                        "final_mark": row[5],
                        "result": result_str,
                        "passed": "ناجح" in result_str,
                    }
                )

        # Format text for Telegram
        formatted_text = format_marks_text(
            filtered_data,
            student_number,
            department_id,
            year_display,
            specialization,
            student_name,
        )

        return (
            jsonify(
                {
                    "student_number": student_number,
                    "student_name": student_name,
                    "department": DEPARTMENTS.get(department_id, "غير محدد"),
                    "academic_year": academic_year,
                    "specialization": specialization,
                    "year_display": year_display,
                    "statistics": stats,
                    "subjects": subjects_list,
                    "missing_subjects": missing,
                    "formatted_text": formatted_text,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error in get_marks API: {e}", exc_info=True)
        return (
            jsonify(
                {
                    "error": "حدث خطأ أثناء جلب النتائج.",
                    "formatted_text": (
                        "❌ حدث خطأ أثناء جلب النتائج.\n\n"
                        "🔧 الأسباب المحتملة:\n"
                        "• مشكلة في الاتصال بالإنترنت\n"
                        "• الموقع غير متاح مؤقتاً\n"
                        "• بيانات غير صحيحة\n\n"
                        "🔄 حاول مرة أخرى بعد قليل."
                    ),
                }
            ),
            500,
        )


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting API server on http://0.0.0.0:{port}")
    print(f"🚀 API server running on http://0.0.0.0:{port}")
    print(f"📖 Endpoints:")
    print(f"   GET  /api/health")
    print(f"   GET  /api/departments")
    print(f"   GET  /api/academic_years")
    print(f"   POST /api/get_marks")
    app.run(host="0.0.0.0", port=port, debug=True)
