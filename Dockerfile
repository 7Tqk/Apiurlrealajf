# استخدام الصورة المحدثة التي تحتوي على Chromium المتوافق مع الإصدار 1.61.0
FROM mcr.microsoft.com/playwright/python:v1.61.0-jammy

# تعيين مجلد العمل
WORKDIR /app

# نسخ ملفات المشروع إلى داخل الحاوية
COPY . .

# تثبيت المكتبات المطلوبة
RUN pip install --no-cache-dir -r requirements.txt

# فتح المنفذ الذي يعمل عليه Uvicorn
EXPOSE 8000

# أمر تشغيل التطبيق
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
