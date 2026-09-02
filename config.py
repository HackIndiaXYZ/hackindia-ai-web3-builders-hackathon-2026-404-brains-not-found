"""Centralized TrafficGuard Pro application settings."""

import os


APP_NAME = "TrafficGuard Pro"
TAGLINE = "AI-powered Indian traffic enforcement"
AUTHOR_NAME = "Pawan Singh"
AUTHOR_ROLE = "Founder & Full-Stack Developer"
AUTHOR_EMAIL = "pawan9140582015@gmail.com"
AUTHOR_GITHUB = "https://github.com/pawan00207"
AUTHOR_LINKEDIN = "Pawan Singh"
EDUCATION = "B.Tech CSE, Delhi Technical Campus (DTC), Greater Noida"
UNIVERSITY = "Guru Gobind Singh Indraprastha University (GGSIPU)"
CGPA = "9.16"
EXPECTED_GRADUATION = "2028"

SECRET_KEY = os.environ.get("SECRET_KEY", "trafficguard-change-in-production")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "pawan123")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "")
REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "reports")
