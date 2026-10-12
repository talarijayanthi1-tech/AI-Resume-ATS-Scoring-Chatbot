"""Resume analyzer: text extraction, ATS score, certification suggestions."""
import io
import re

import docx
import pdfplumber

SECTIONS = {
    "summary/objective": ["summary", "objective", "profile", "about me"],
    "education": ["education", "academic"],
    "skills": ["skills", "technical skills", "technologies"],
    "projects": ["projects", "project"],
    "experience": ["experience", "internship", "work history", "employment"],
    "certifications": ["certification", "certifications", "courses", "achievements"],
}

ACTION_VERBS = [
    "developed", "built", "designed", "implemented", "created", "led", "managed",
    "improved", "optimized", "analyzed", "deployed", "automated", "trained",
    "integrated", "collaborated", "delivered", "reduced", "increased", "achieved",
]

# domain -> (skill keywords, certification suggestions)
DOMAINS = {
    "AI / Machine Learning": (
        ["machine learning", "deep learning", "tensorflow", "keras", "pytorch",
         "scikit", "nlp", "neural", "opencv", "pandas", "numpy", "ai", "ml"],
        [
            "Machine Learning Specialization - Coursera (DeepLearning.AI)",
            "TensorFlow Developer Certificate - Google",
            "Microsoft Azure AI Fundamentals (AI-900)",
            "IBM AI Engineering Professional Certificate",
        ],
    ),
    "Data / Analytics": (
        ["sql", "excel", "power bi", "tableau", "data analysis", "statistics",
         "mysql", "data visualization", "analytics"],
        [
            "Google Data Analytics Professional Certificate",
            "Microsoft Power BI Data Analyst (PL-300)",
            "IBM Data Science Professional Certificate",
        ],
    ),
    "Web Development": (
        ["html", "css", "javascript", "react", "node", "django", "flask",
         "angular", "php", "bootstrap", "mongodb", "express"],
        [
            "Meta Front-End Developer Certificate - Coursera",
            "freeCodeCamp Responsive Web Design / JavaScript Algorithms",
            "The Odin Project / Full Stack Open (University of Helsinki)",
        ],
    ),
    "Cloud / DevOps": (
        ["aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "git",
         "linux", "ci/cd", "terraform"],
        [
            "AWS Certified Cloud Practitioner",
            "Microsoft Azure Fundamentals (AZ-900)",
            "Google Cloud Digital Leader",
        ],
    ),
    "Programming / Core CS": (
        ["python", "java", "c++", "c programming", "data structures",
         "algorithms", "oop", "dsa", "kotlin", "golang"],
        [
            "Python Institute PCAP / PCEP Certification",
            "Oracle Certified Java SE Associate",
            "NPTEL - Data Structures and Algorithms (IIT)",
        ],
    ),
    "Cybersecurity": (
        ["security", "cybersecurity", "ethical hacking", "network security",
         "penetration", "cryptography", "wireshark"],
        [
            "Google Cybersecurity Professional Certificate",
            "CompTIA Security+",
            "Certified Ethical Hacker (CEH)",
        ],
    ),
}

GENERAL_CERTS = [
    "NPTEL - Programming, Data Structures and Algorithms using Python",
    "Google IT Automation with Python - Coursera",
    "AWS Certified Cloud Practitioner",
]


def extract_text(data: bytes, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    if name.endswith(".docx"):
        d = docx.Document(io.BytesIO(data))
        parts = [p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                parts.extend(c.text for c in row.cells)
        return "\n".join(parts)
    if name.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")
    raise ValueError("Unsupported file type. Send PDF, DOCX or TXT.")


def _has(text: str, kw: str) -> bool:
    return re.search(r"(?<![a-z0-9+#])" + re.escape(kw) + r"(?![a-z0-9+#])", text) is not None


def _tokens(text: str) -> set:
    return set(re.findall(r"[a-z][a-z+#.]{2,}", text.lower()))


STOP = set("and the for with you our are will have this that from your able work "
           "team role job years year experience knowledge skills good strong".split())


def analyze(text: str, job_description: str = "") -> dict:
    low = text.lower()
    words = re.findall(r"\w+", text)
    tips, score = [], 0

    # 1. Contact info (10)
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    phone = re.search(r"(\+?\d[\d\s-]{8,}\d)", text)
    c = (5 if email else 0) + (5 if phone else 0)
    score += c
    if not email: tips.append("Add a professional email address")
    if not phone: tips.append("Add a phone number")

    # 2. Sections (25)
    found = [s for s, keys in SECTIONS.items() if any(k in low for k in keys)]
    score += round(25 * len(found) / len(SECTIONS))
    for s in SECTIONS:
        if s not in found:
            tips.append(f"Add a '{s.title()}' section")

    # 3. Skills / keyword match (25)
    all_kw = {k for kws, _ in DOMAINS.values() for k in kws}
    hits = sorted(k for k in all_kw if _has(low, k))
    if job_description.strip():
        jd_tokens = {t for t in _tokens(job_description) if t not in STOP}
        match = jd_tokens & _tokens(text)
        pct = len(match) / max(len(jd_tokens), 1)
        score += round(25 * min(pct / 0.5, 1))  # 50% match = full marks
        missing = sorted(jd_tokens - _tokens(text))[:8]
        if missing:
            tips.append("Missing JD keywords: " + ", ".join(missing))
    else:
        score += min(25, len(hits) * 2)
        if len(hits) < 8:
            tips.append("List more relevant technical skills/keywords")

    # 4. Action verbs (10)
    verbs = [v for v in ACTION_VERBS if _has(low, v)]
    score += min(10, len(verbs) * 2)
    if len(verbs) < 4:
        tips.append("Start bullets with action verbs (built, developed, optimized)")

    # 5. Quantified results (10)
    nums = re.findall(r"\d+\s*%|\b\d{2,}\+?\b", text)
    score += min(10, len(nums) * 2)
    if len(nums) < 3:
        tips.append("Add measurable results (e.g. 'improved accuracy by 15%')")

    # 6. Length (10)
    n = len(words)
    if 250 <= n <= 900:
        score += 10
    elif 150 <= n < 250 or 900 < n <= 1200:
        score += 5
        tips.append("Keep resume around 1 page (250-900 words)")
    else:
        tips.append("Resume is too short/long; aim for 250-900 words")

    # 7. Links (10)
    links = (5 if "linkedin" in low else 0) + (5 if "github" in low else 0)
    score += links
    if "linkedin" not in low: tips.append("Add your LinkedIn link")
    if "github" not in low: tips.append("Add your GitHub link")

    return {
        "score": min(score, 100),
        "sections": found,
        "skills": hits[:10],
        "tips": tips[:5],
        "certs": suggest_certs(low),
        "words": n,
    }


def suggest_certs(low: str) -> list:
    ranked = sorted(
        DOMAINS.items(),
        key=lambda kv: sum(_has(low, k) for k in kv[1][0]),
        reverse=True,
    )
    certs = []
    for name, (kws, cs) in ranked:
        if sum(_has(low, k) for k in kws) == 0:
            break
        for c in cs:
            if c not in certs:
                certs.append(c)
            if len(certs) == 3:
                return certs
        # take at most 2 from the top domain so the list mixes areas
        if len(certs) >= 2 and name == ranked[0][0]:
            certs = certs[:2]
    for c in GENERAL_CERTS:
        if c not in certs:
            certs.append(c)
        if len(certs) == 3:
            break
    return certs[:3]
