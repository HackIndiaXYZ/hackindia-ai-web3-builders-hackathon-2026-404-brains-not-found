"""Centralized TrafficGuard Pro application settings."""

import os

# App Information
APP_NAME = "TrafficGuard Pro"
TAGLINE = "AI-powered Indian traffic enforcement"
ORGANIZATION = "Ministry of Road Transport & Highways — AI Enforcement Division"
MOTTO = "सत्यमेव जयते · AI for Road Safety"

# Author Information
AUTHOR_NAME = "Pawan Singh"
AUTHOR_ROLE = "Founder & Full-Stack AI Engineer"
AUTHOR_EMAIL = "pawan9140582015@gmail.com"
AUTHOR_GITHUB = "https://github.com/pawan00207"
AUTHOR_LINKEDIN = "Pawan Singh"
EDUCATION = "B.Tech CSE, Delhi Technical Campus (DTC), Greater Noida"
UNIVERSITY = "Guru Gobind Singh Indraprastha University (GGSIPU)"
CGPA = "9.16"
EXPECTED_GRADUATION = "2028"

# Security & Session
SECRET_KEY = os.environ.get("SECRET_KEY", "trafficguard-hackathon-2026-secret-key")

# Multi-Role RBAC Passwords (can be overridden via env vars)
SUPERADMIN_PASSWORD = os.environ.get("SUPERADMIN_PASSWORD", "superadmin123")
ADMIN_PASSWORD      = os.environ.get("ADMIN_PASSWORD", "pawan123")
INSPECTOR_PASSWORD  = os.environ.get("INSPECTOR_PASSWORD", "inspector123")
OFFICER_PASSWORD    = os.environ.get("OFFICER_PASSWORD", "officer123")
DEMO_PASSWORD       = os.environ.get("DEMO_PASSWORD", "demo123")

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(BASE_DIR, "static", "reports")
SCREENSHOT_DIR = os.path.join(BASE_DIR, "static", "screenshots")
CHALLAN_DIR = os.path.join(BASE_DIR, "static", "challans")
RECEIPT_DIR = os.path.join(BASE_DIR, "static", "receipts")
VIDEO_FOLDER = os.path.join(BASE_DIR, "videos")
LOG_DIR = os.path.join(BASE_DIR, "logs")

for d in [REPORT_DIR, SCREENSHOT_DIR, CHALLAN_DIR, RECEIPT_DIR, VIDEO_FOLDER, LOG_DIR]:
    os.makedirs(d, exist_ok=True)

# External API Integrations (Plug-and-play with offline fallbacks)
VAHAN_API_KEY = os.environ.get("VAHAN_API_KEY", "")
VAHAN_API_URL = os.environ.get("VAHAN_API_URL", "https://vahan.parivahan.gov.in/vahanservice/vahan/api/rc-details")

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN  = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
TWILIO_SMS_NUMBER = os.environ.get("TWILIO_SMS_NUMBER", "")

WA_PHONE_ID = os.environ.get("WA_PHONE_ID", "")
WA_TOKEN    = os.environ.get("WA_TOKEN", "")

GMAIL_ADDRESS      = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASS", "")

CITIZEN_WA_NUMBER = os.environ.get("CITIZEN_WA", "+919876543210")
ADMIN_WA_NUMBER   = os.environ.get("ADMIN_WA", "+919876543211")
CITIZEN_EMAIL     = os.environ.get("CITIZEN_EMAIL", "citizen.demo@trafficguard.in")
ADMIN_EMAIL       = os.environ.get("ADMIN_EMAIL", "admin.demo@trafficguard.in")

# AI / LLM API Key (Optional — Saarthi AI has built-in offline NLP engine)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Payment Gateway (Razorpay Test Keys)
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_trafficguard_2026")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "mock_secret_key_trafficguard")
