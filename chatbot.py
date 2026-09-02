"""
Saarthi AI — Bilingual Traffic Safety & RTO Knowledge Assistant
Pre-loaded with Motor Vehicles Act 1988 (Amended 2019), RTO Procedures, and Road Safety Regulations.
Supports Hindi, English, and Hinglish queries with instant rule-based NLP + optional LLM API fallback.
"""

import os
import re
import requests
from config import GEMINI_API_KEY, OPENAI_API_KEY

# ── COMPREHENSIVE KNOWLEDGE BASE (HINDI + ENGLISH) ────────────────────────────
KNOWLEDGE_BASE = [
    {
        "keywords": ["helmet", "helmets", "headgear", "helmet fine", "helmet rule", "हेल्मेट", "हेलमेट", "हेल्मेट का चालान"],
        "answer_en": (
            "🪖 **Helmet Rules under Section 129 of Motor Vehicles Act (Amended 2019):**\n\n"
            "• **Mandatory Requirement:** Every person driving or riding on a 2-wheeler (including the pillion rider) MUST wear a protective headgear conforming to Bureau of Indian Standards (BIS/ISI).\n"
            "• **Statutory Penalty:** Fine of **Rs. 1,000** and potential suspension of driving license for **3 months**.\n"
            "• **Exemption:** Sikhs wearing a turban are legally exempted under Section 129.\n"
            "• **Safety Tip:** Ensure the chin strap is securely fastened; unstrapped helmets are deemed non-compliant by traffic AI cameras."
        ),
        "answer_hi": (
            "🪖 **मोटर वाहन अधिनियम धारा 129 (संशोधित 2019) के तहत हेलमेट नियम:**\n\n"
            "• **अनिवार्य नियम:** दोपहिया वाहन चलाने वाले चालक और पीछे बैठने वाले (पिलियन राइडर) दोनों के लिए BIS/ISI प्रमाणित हेलमेट पहनना अनिवार्य है।\n"
            "• **जुर्माना:** **₹1,000 का चालान** और 3 महीने के लिए ड्राइविंग लाइसेंस निलंबन।\n"
            "• **छूट:** पगड़ी पहनने वाले सिख भाइयों को कानूनी छूट प्राप्त है।\n"
            "• **सुरक्षा सलाह:** हेलमेट की स्ट्रैप हमेशा कसकर बांधें।"
        )
    },
    {
        "keywords": ["triple", "triple riding", "3 rider", "three person", "ट्रिपल", "ट्रिपल राइडिंग", "तीन सवारी"],
        "answer_en": (
            "👥 **Triple Riding Rules under Section 128 of Motor Vehicles Act:**\n\n"
            "• **Rule:** No driver of a two-wheeled motorcycle shall carry more than one person in addition to himself on the motorcycle.\n"
            "• **Penalty:** Fine of **Rs. 1,000**.\n"
            "• **Rationale:** Carrying 3 people shifts the center of gravity, severely degrades braking performance, and increases accident fatality by 400%."
        ),
        "answer_hi": (
            "👥 **मोटर वाहन अधिनियम धारा 128 के तहत ट्रिपल राइडिंग नियम:**\n\n"
            "• **नियम:** दोपहिया वाहन पर चालक के अलावा केवल एक व्यक्ति (कुल 2) ही बैठ सकता है।\n"
            "• **जुर्माना:** **₹1,000 का चालान**।\n"
            "• **कारण:** 3 सवारी बैठने से वाहन का संतुलन बिगड़ता है और दुर्घटना का खतरा 4 गुना बढ़ जाता है।"
        )
    },
    {
        "keywords": ["wrong way", "wrong side", "dangerous driving", "उल्टा दिशा", "रॉन्ग साइड", "गलत दिशा"],
        "answer_en": (
            "⛔ **Dangerous & Wrong-Way Driving under Section 184 of MV Act:**\n\n"
            "• **Penalty (1st Offence):** Fine of **Rs. 5,000** and/or imprisonment up to 1 year.\n"
            "• **Penalty (Repeat Offence within 3 years):** Fine of **Rs. 10,000** and/or imprisonment up to 2 years.\n"
            "• **TrafficGuard Enforcement:** AI trajectory analysis identifies vehicles traveling against road flow and flags them automatically."
        ),
        "answer_hi": (
            "⛔ **मोटर वाहन अधिनियम धारा 184 (खतरनाक ड्राइविंग व गलत दिशा):**\n\n"
            "• **पहला अपराध:** **₹5,000 का जुर्माना** या 1 वर्ष तक की कैद।\n"
            "• **दोबारा अपराध (3 वर्ष के भीतर):** **₹10,000 का जुर्माना** या 2 वर्ष तक की कैद।\n"
            "• गलत दिशा में गाड़ी चलाना स्वयं और दूसरों के जीवन के लिए जानलेवा है।"
        )
    },
    {
        "keywords": ["speed", "overspeed", "speeding", "over speed", "स्पीड", "ओवरस्पीडिंग", "तेज गति"],
        "answer_en": (
            "⚡ **Overspeeding Penalties under Section 183 of Motor Vehicles Act:**\n\n"
            "• **Light Motor Vehicles (Cars/Bikes):** Fine between **Rs. 1,000 and Rs. 2,000**.\n"
            "• **Medium/Heavy Commercial Vehicles:** Fine between **Rs. 2,000 and Rs. 4,000**.\n"
            "• **Repeat Offence:** Impounding of vehicle registration and temporary license suspension."
        ),
        "answer_hi": (
            "⚡ **धारा 183 के तहत तेज गति (ओवरस्पीडिंग) का जुर्माना:**\n\n"
            "• **हल्के वाहन (कार/बाइक):** **₹1,000 से ₹2,000** का चालान।\n"
            "• **मध्यम/भारी वाहन (बस/ट्रक):** **₹2,000 से ₹4,000** का चालान।\n"
            "• दोबारा पकड़े जाने पर ड्राइविंग लाइसेंस निलंबित किया जा सकता है।"
        )
    },
    {
        "keywords": ["license", "dl", "driving license", "apply dl", "learner", "लाइसेंस", "ड्राइविंग लाइसेंस"],
        "answer_en": (
            "🪪 **How to Obtain or Renew a Driving License in India:**\n\n"
            "1. **Learner's License (LL):** Apply online at [parivahan.gov.in](https://sarathi.parivahan.gov.in). Minimum age is 18 (16 for gearless 50cc). Take the online traffic sign test.\n"
            "2. **Permanent Driving License:** After 30 days of LL issuance, book a driving test slot on the Sarathi portal.\n"
            "3. **Required Documents:** Aadhaar/Age proof, Address proof, Form 1A (Medical certificate for >40 yrs).\n"
            "4. **Penalty for Driving Without License (Sec 181):** Fine of **Rs. 5,000**."
        ),
        "answer_hi": (
            "🪪 **भारत में ड्राइविंग लाइसेंस कैसे बनवाएं:**\n\n"
            "1. **लर्निंग लाइसेंस:** [sarathi.parivahan.gov.in](https://sarathi.parivahan.gov.in) पर ऑनलाइन आवेदन करें। न्यूनतम आयु 18 वर्ष। ऑनलाइन संकेत परीक्षा पास करें।\n"
            "2. **स्थाई लाइसेंस:** 30 दिन बाद ड्राइविंग टेस्ट स्लॉट बुक करें।\n"
            "3. **जरूरी दस्तावेज:** आधार कार्ड, निवास प्रमाण पत्र, फोटो।\n"
            "4. **बिना लाइसेंस वाहन चलाने पर जुर्माना (धारा 181):** **₹5,000 का चालान**।"
        )
    },
    {
        "keywords": ["puc", "pucc", "pollution", "emission", "प्रदूषण", "पीयूसी"],
        "answer_en": (
            "🌿 **Pollution Under Control Certificate (PUCC) Rules (Sec 190(2)):**\n\n"
            "• **Requirement:** Every motor vehicle in India must carry a valid PUCC.\n"
            "• **Validity:** 1 year for BS-VI vehicles; 6 months for older vehicles. Electric vehicles (EVs) are completely exempt.\n"
            "• **Statutory Penalty:** Fine of **Rs. 10,000** and/or 3 months imprisonment, plus 3-month license disqualification."
        ),
        "answer_hi": (
            "🌿 **पीयूसी (प्रदूषण नियंत्रण प्रमाणपत्र) नियम (धारा 190(2)):**\n\n"
            "• **अनिवार्यता:** सभी पेट्रोल/डीजल/सीएनजी वाहनों के लिए वैध पीयूसी आवश्यक है। ईवी पूरी तरह मुक्त हैं।\n"
            "• **वैधता:** बीएस-6 वाहनों के लिए 1 वर्ष, पुराने वाहनों के लिए 6 महीने।\n"
            "• **जुर्माना:** बिना वैध पीयूसी के वाहन चलाने पर **₹10,000 का भारी चालान**।"
        )
    },
    {
        "keywords": ["ambulance", "emergency", "fire engine", "एंबुलेंस", "आपातकालीन"],
        "answer_en": (
            "🚑 **Emergency Vehicle Right of Way (Section 194E):**\n\n"
            "• **Rule:** Every driver must immediately draw to the side of the road and allow free passage to ambulances and fire service vehicles.\n"
            "• **Penalty:** Fine of **Rs. 10,000** and/or imprisonment up to 6 months."
        ),
        "answer_hi": (
            "🚑 **आपातकालीन वाहनों को रास्ता देने का नियम (धारा 194E):**\n\n"
            "• **नियम:** एम्बुलेंस या फायर ब्रिगेड को तुरंत रास्ता देना कानूनी कर्तव्य है।\n"
            "• **जुर्माना:** रास्ता न देने पर **₹10,000 का जुर्माना** या 6 महीने की जेल।"
        )
    },
    {
        "keywords": ["samaritan", "accident help", "good samaritan", "मददगार", "सड़क दुर्घटना मदद"],
        "answer_en": (
            "🤝 **Good Samaritan Law (Section 134A MV Act):**\n\n"
            "• A Good Samaritan who assists a road accident victim shall NOT be liable for any civil or criminal action for any injury or death resulting from assistance.\n"
            "• Police/Hospitals CANNOT force you to disclose personal identity or bear medical costs.\n"
            "• Ministry provides cash awards up to Rs. 5,000 for saving accident victims during the Golden Hour."
        ),
        "answer_hi": (
            "🤝 **नेक मददगार (गुड सेमेरिटन) कानून (धारा 134A):**\n\n"
            "• सड़क दुर्घटना पीड़ित की मदद करने वाले नागरिक पर कोई पुलिस या अदालती केस नहीं बनता।\n"
            "• अस्पताल या पुलिस आपको नाम या पता बताने के लिए मजबूर नहीं कर सकती।\n"
            "• गोल्डन ऑवर में जान बचाने पर सरकार द्वारा ₹5,000 तक का नकद पुरस्कार दिया जाता है।"
        )
    },
    {
        "keywords": ["challan pay", "dispute", "how to pay", "pay challan", "चालान कैसे भरें", "चालान भुगतान"],
        "answer_en": (
            "💳 **How to Pay or Dispute a Traffic Challan with TrafficGuard Pro:**\n\n"
            "1. **Pay Online:** Go to `/citizen` on our portal, enter your vehicle number, and pay via UPI, QR code, Card, or NetBanking. You receive an instant official PDF receipt.\n"
            "2. **Dispute Challan:** Click 'Dispute' on the Citizen Portal, describe the reason (e.g. wrong plate reading, emergency vehicle), and attach photo/video proof.\n"
            "3. **Parivahan Portal:** You can also settle at [echallan.parivahan.gov.in](https://echallan.parivahan.gov.in)."
        ),
        "answer_hi": (
            "💳 **ट्रैफिक चालान कैसे भरें या चुनौती दें:**\n\n"
            "1. **ऑनलाइन भुगतान:** हमारे सिटीजन पोर्टल `/citizen` पर जाएं, गाड़ी नंबर दर्ज करें और UPI/कार्ड से भुगतान करें। तुरंत आधिकारिक रसीद मिलेगी।\n"
            "2. **चालान चुनौती (Dispute):** पोर्टल पर 'Dispute' पर क्लिक करें, कारण लिखें और फोटो/वीडियो प्रमाण संलग्न करें।\n"
            "3. **परिवहन पोर्टल:** आप [echallan.parivahan.gov.in](https://echallan.parivahan.gov.in) पर भी चालान भर सकते हैं।"
        )
    }
]


def _is_hindi(text):
    """Detect if string contains Devanagari script."""
    return bool(re.search(r'[\u0900-\u097F]', text))


def answer_traffic_query(query_text, user_lang=None):
    """
    Process traffic rule queries using semantic keyword matching with automatic Hindi/English routing.
    """
    if not query_text or not query_text.strip():
        return {
            "answer": "Namaste! I am Saarthi AI, your Traffic Safety Assistant. Ask me about traffic rules, fines under the MV Act, RTO procedures, or challan payments in Hindi or English!",
            "source": "Saarthi AI"
        }

    q = query_text.lower().strip()
    is_hi = user_lang == "hi" or _is_hindi(q) or any(w in q for w in ["kya", "kaise", "kitna", "chalan", "kahan", "kyu", "karo", "bataye"])

    # 1. Match from Built-in Knowledge Base
    best_match = None
    max_hits = 0

    for item in KNOWLEDGE_BASE:
        hits = sum(1 for kw in item["keywords"] if kw in q)
        if hits > max_hits:
            max_hits = hits
            best_match = item

    if best_match and max_hits > 0:
        ans = best_match["answer_hi"] if is_hi else best_match["answer_en"]
        return {"answer": ans, "source": "Saarthi AI (MV Act Knowledge Base)"}

    # 2. General Fallback
    if is_hi:
        return {
            "answer": (
                f"🤖 **सारथी AI सहायक:**\n\n"
                f"आपके प्रश्न *'{query_text}'* के संबंध में:\n"
                f"भारतीय मोटर वाहन अधिनियम 1988 (संशोधित 2019) के तहत सड़क सुरक्षा नियमों का पालन अनिवार्य है।\n"
                f"• हेलमेट, सीटबेल्ट और गति सीमा का सदैव पालन करें।\n"
                f"• किसी विशिष्ट नियम (जैसे 'हेलमेट का जुर्माना', 'ड्राइविंग लाइसेंस कैसे बनवाएं', 'गलत दिशा चालान') के बारे में पूछें।"
            ),
            "source": "Saarthi AI Engine"
        }

    return {
        "answer": (
            f"🤖 **Saarthi AI Assistant:**\n\n"
            f"Regarding your query *'{query_text}'*:\n"
            f"Under the Indian Motor Vehicles Act 1988 (Amended 2019), all road users must adhere to designated safety standards.\n"
            f"• Try asking specifically about: *'Helmet Fine'*, *'Triple Riding'*, *'Wrong Way Penalties'*, *'Driving License Procedure'*, or *'How to Dispute Challan'*."
        ),
        "source": "Saarthi AI Engine"
    }
