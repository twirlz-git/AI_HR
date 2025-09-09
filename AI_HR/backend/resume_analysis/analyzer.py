import json
import os
import re
import tempfile
import urllib.parse
from typing import Dict, Optional

from openai import OpenAI

try:
    import pymupdf4llm  # PDF extractor
except Exception:
    pymupdf4llm = None
try:
    import docx  # python-docx
except Exception:
    docx = None


LLM_MODEL = "anthropic/claude-3.5-sonnet"
_client: Optional[OpenAI] = None


def init_llm_client(api_key: Optional[str]) -> None:
    global _client
    if api_key:
        _client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)


def detect_language(text: str) -> str:
    return 'ru' if any('\u0400' <= char <= '\u04FF' for char in text) else 'en'


prompts = {
    "en": {
        "system_candidate": "Let's think step by step. Return ONLY JSON.",
        "user_candidate": (
            "Analyze this CV. Return ONLY valid JSON with keys: "
            "candidate_name, phone_number, email, degree, experience, technical_skill, "
            "responsibility, certificate, soft_skill, comment.\n\n{cv_content}"
        ),
        "system_job": "Let's think step by step. Return ONLY JSON.",
        "user_job": (
            "Analyze this job description. Return ONLY valid JSON with keys: "
            "degree, experience, technical_skill, responsibility, certificate, soft_skill.\n\n{job_description}"
        ),
        "system_matching": (
            "Compare candidate and job. Return ONLY JSON with sections degree, experience, technical_skill, "
            "responsibility, certificate, soft_skill (each has score and comment), and summary_comment."
        ),
        "user_matching": (
            "JOB REQUIREMENTS: {job_json}\nCANDIDATE PROFILE: {candidate_json}\nReturn ONLY JSON."
        ),
    },
    "ru": {
        "system_candidate": "Давай рассуждать по шагам. Верни ТОЛЬКО JSON.",
        "user_candidate": (
            "Проанализируй резюме. Верни ТОЛЬКО валидный JSON со значениями: "
            "candidate_name, phone_number, email, degree, experience, technical_skill, responsibility, certificate, soft_skill, comment.\n\n{cv_content}"
        ),
        "system_job": "Давай рассуждать по шагам. Верни ТОЛЬКО JSON.",
        "user_job": (
            "Проанализируй описание вакансии. Верни ТОЛЬКО валидный JSON: "
            "degree, experience, technical_skill, responsibility, certificate, soft_skill.\n\n{job_description}"
        ),
        "system_matching": (
            "Сравни кандидата и вакансию. Верни ТОЛЬКО JSON с разделами degree, experience, technical_skill, "
            "responsibility, certificate, soft_skill (каждый со score и comment), и summary_comment."
        ),
        "user_matching": (
            "ТРЕБОВАНИЯ ВАКАНСИИ: {job_json}\nПРОФИЛЬ КАНДИДАТА: {candidate_json}\nВерни ТОЛЬКО JSON."
        ),
    },
}


def _extract_json(content: str) -> Dict:
    try:
        return json.loads(content)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", content)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return {}
        return {}


def analyze_candidate(cv_content: str) -> Dict:
    if not _client:
        return {"candidate_name": "Unknown", "comment": "LLM not configured"}
    lang = detect_language(cv_content)
    system_prompt = prompts[lang]["system_candidate"]
    user_prompt = prompts[lang]["user_candidate"].format(cv_content=cv_content)
    completion = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.1,
    )
    return _extract_json(completion.choices[0].message.content) or {"candidate_name": "Unknown"}


def analyze_job(job_description: str) -> Dict:
    if not _client:
        return {"degree": [], "experience": [], "technical_skill": [], "responsibility": [], "certificate": [], "soft_skill": []}
    lang = detect_language(job_description)
    system_prompt = prompts[lang]["system_job"]
    user_prompt = prompts[lang]["user_job"].format(job_description=job_description)
    completion = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.1,
    )
    return _extract_json(completion.choices[0].message.content) or {}


def analyze_matching(job: Dict, candidate: Dict) -> Dict:
    if not _client:
        return {"score": 0.0, "summary_comment": "LLM not configured"}
    lang = detect_language(json.dumps(candidate, ensure_ascii=False))
    system_prompt = prompts[lang]["system_matching"]
    user_prompt = prompts[lang]["user_matching"].format(
        job_json=json.dumps(job, ensure_ascii=False), candidate_json=json.dumps(candidate, ensure_ascii=False)
    )
    completion = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.1,
    )
    result = _extract_json(completion.choices[0].message.content) or {}
    weights = {"degree": 0.1, "experience": 0.2, "technical_skill": 0.3, "responsibility": 0.25, "certificate": 0.1, "soft_skill": 0.05}
    try:
        weighted = sum((result.get(k, {}).get("score", 0) or 0) * w for k, w in weights.items())
        result["score"] = round(float(weighted), 2)
    except Exception:
        result["score"] = 0.0
    return result


def _clean_text(raw_text: str) -> str:
    text = urllib.parse.unquote(raw_text or "")
    text = text.replace('\\n', '\n').replace('\u200b', '')
    text = re.sub(r'\[(https?://.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'^\s*[●*]\s*', '- ', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return '\n'.join([line.strip() for line in text.split('\n')]).strip()


def parse_upload_to_text(upload) -> str:
    suffix = os.path.splitext(getattr(upload, 'filename', '') or '')[1].lower()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            data = upload.file.read()
            tmp.write(data)
            tmp_path = tmp.name
        if suffix == '.pdf' and pymupdf4llm:
            txt = pymupdf4llm.to_markdown(tmp_path)
            return _clean_text(txt)
        if suffix in ('.docx', '.doc') and docx:
            try:
                d = docx.Document(tmp_path)
                txt = '\n'.join([p.text for p in d.paragraphs])
                return _clean_text(txt)
            except Exception:
                pass
        try:
            return _clean_text(data.decode('utf-8', errors='ignore'))
        except Exception:
            return ''
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


