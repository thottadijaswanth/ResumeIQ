import re
from typing import Dict, List, Optional, Tuple
from backend.app.matching.experience_matcher import ExperienceMatcher
from backend.app.matching.normalizer import SKILL_ALIASES
from backend.app.schemas.resume import (
    EducationItem,
    ExperienceItem,
    ProjectItem,
    StructuredResume,
)

_LOCATION_LINE_RE = re.compile(
    r"\b(hyderabad|bangalore|bengaluru|chennai|pune|mumbai|delhi|noida|gurgaon|gurugram|"
    r"kolkata|ahmedabad|visakhapatnam|remote|san francisco|new york|seattle|austin|"
    r"boston|chicago|london|toronto|berlin|singapore|karnataka|india|usa|united states|uk)\b",
    re.IGNORECASE,
)

_DEGREE_RE = re.compile(
    r"(Bachelor(?:'s)?|Master(?:'s)?|Ph\.?D\.?|Doctorate|B\.?S\.?|M\.?S\.?|B\.?Tech|M\.?Tech|B\.?E\.?|Diploma|SSC|HSC|MBA)\s*(?:of|in|-)?\s*([A-Za-z &/]+)?",
    re.IGNORECASE,
)

_DATE_RANGE_RE = re.compile(
    r"((?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+)?(?:19|20)\d{2}|(?:0?[1-9]|1[0-2])[/\-](?:19|20)\d{2})\s*"
    r"(?:-|–|—|to)+\s*"
    r"((?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+)?(?:19|20)\d{2}|(?:0?[1-9]|1[0-2])[/\-](?:19|20)\d{2}|Present|Current|Now|Ongoing|Till\s+Date)",
    re.IGNORECASE,
)

_INLINE_DURATION_RE = re.compile(
    r"(\d+(?:\.\d+)?\s*\+?\s*(?:years?|yrs?|months?|mos?))\b",
    re.IGNORECASE,
)

_ROLE_WORD_RE = re.compile(
    r"\b([A-Za-z0-9 /&+\-]{0,45}?(?:Engineer|Developer|Architect|Intern|Trainee|Lead|Manager|Scientist|Analyst|Consultant|Programmer|Administrator|Specialist))\b",
    re.IGNORECASE,
)

_ACADEMIC_LINE_RE = re.compile(
    r"\b(b\.?tech|m\.?tech|b\.?e\.?|b\.?s\.?|m\.?s\.?|bachelor|master|diploma|ssc|hsc|"
    r"university|college|school|institute|cgpa|gpa|student|certificate|certification|course)\b",
    re.IGNORECASE,
)

# Canonical section headings
_SECTION_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("experience", re.compile(r"^(?:work\s+|professional\s+|industry\s+|industrial\s+)?(?:experience|employment(?:\s+history)?|internships?|career\s+history)$", re.IGNORECASE)),
    ("education", re.compile(r"^(?:education(?:\s+&\s+qualifications)?|academics?|academic\s+background|qualifications)$", re.IGNORECASE)),
    ("projects", re.compile(r"^(?:key\s+|academic\s+|personal\s+|technical\s+)?projects$", re.IGNORECASE)),
    ("skills", re.compile(r"^(?:technical\s+|core\s+)?skills(?:\s+&\s+tools)?$", re.IGNORECASE)),
    ("summary", re.compile(r"^(?:professional\s+|career\s+)?(?:summary|profile|objective|about\s+me)$", re.IGNORECASE)),
    ("certifications", re.compile(r"^(?:certifications?(?:\s+&\s+achievements)?|achievements|awards|honors|licenses)$", re.IGNORECASE)),
]


def _classify_section_heading(line: str) -> Optional[str]:
    cleaned = re.sub(r"[:\-_|•]+$", "", line.strip()).strip()
    if not cleaned or len(cleaned) > 45 or len(cleaned.split()) > 5:
        return None
    for sec_name, pattern in _SECTION_PATTERNS:
        if pattern.match(cleaned):
            return sec_name
    return None


def _split_sections(lines: List[str]) -> Tuple[Dict[str, List[str]], bool]:
    """
    Partition resume lines into canonical sections.
    Returns (sections_dict, has_explicit_sections).
    """
    sections: Dict[str, List[str]] = {"header": []}
    current = "header"
    found_headers = 0

    for line in lines:
        sec = _classify_section_heading(line)
        if sec is not None:
            current = sec
            sections.setdefault(current, [])
            found_headers += 1
        else:
            sections.setdefault(current, []).append(line)

    return sections, found_headers > 0


class FastCandidateExtractor:
    """
    Section-aware deterministic resume parser.
    Strictly separates Experience / Internships from Summary, Projects, Certifications,
    and Education so education dates or summaries are never counted as work experience.
    """

    @staticmethod
    def _extract_skills(raw_text: str) -> Tuple[List[str], Dict[str, List[str]]]:
        text_lower = raw_text.lower()
        seen: Dict[str, str] = {}

        for alias, (canonical, category) in SKILL_ALIASES.items():
            pattern = rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])"
            if re.search(pattern, text_lower):
                seen[canonical] = category

        all_skills = sorted(seen.keys())
        by_cat: Dict[str, List[str]] = {
            "Programming Languages": [],
            "Frameworks": [],
            "Databases": [],
            "Cloud": [],
            "DevOps": [],
            "Tools": [],
            "AI/ML": [],
        }
        for skill, cat in seen.items():
            if cat in by_cat:
                by_cat[cat].append(skill)

        return all_skills, by_cat

    @staticmethod
    def _extract_name(lines: List[str], fallback_name: str = "") -> str:
        for line in lines[:5]:
            words = line.split()
            if 2 <= len(words) <= 4 and not any(
                ch in line for ch in ["@", "http", ".com", "|", "/", ":", "•", ","]
            ):
                if not any(
                    kw in line.lower()
                    for kw in ["resume", "curriculum", "summary", "experience", "skills", "education", "certificate"]
                ):
                    return line
        return fallback_name or "Candidate"

    @staticmethod
    def _extract_location(lines: List[str]) -> str:
        for line in lines[:10]:
            m = _LOCATION_LINE_RE.search(line)
            if m:
                clean = line.strip()
                if len(clean) <= 90 and "@" not in clean:
                    parts = [p.strip() for p in re.split(r"[|•]", clean) if _LOCATION_LINE_RE.search(p)]
                    if parts:
                        return parts[0][:80]
                return m.group(0).title()
        return "Unknown"

    @staticmethod
    def _parse_role_and_company(header_line: str) -> Tuple[str, str]:
        """Split lines like 'Java Backend Developer — TechNova Solutions' or 'Intern at Acme'."""
        line = header_line.strip()
        for sep in (" — ", " – ", " - ", " at ", " @ ", " | "):
            if sep in line:
                left, right = line.split(sep, 1)
                return left.strip()[:80], right.split("|")[0].split("(")[0].strip()[:80]
        role_m = _ROLE_WORD_RE.search(line)
        role = role_m.group(1).strip() if role_m else line[:80]
        return role, "Employer"

    @classmethod
    def _extract_experience_from_lines(
        cls,
        exp_lines: List[str],
        all_skills: List[str],
    ) -> List[ExperienceItem]:
        """
        Extract real job / internship entries from work-experience lines.
        Only creates an entry when grounded in a date timeline or explicit role+duration,
        skipping academic/education lines.
        """
        experiences: List[ExperienceItem] = []
        used_line_indices = set()

        for idx, line in enumerate(exp_lines):
            if idx in used_line_indices or _ACADEMIC_LINE_RE.search(line):
                continue

            # Case 1: Line contains a date range like "Jul 2025 – Present" or "2020-2023"
            date_m = _DATE_RANGE_RE.search(line)
            if date_m:
                start_d = date_m.group(1).strip()
                end_d = date_m.group(2).strip().title()

                # Check if role/company is on the same line (before the date) or the previous line
                before_date = line[: date_m.start()].strip(" -–|,()")
                if before_date and len(before_date) >= 3 and not _ACADEMIC_LINE_RE.search(before_date):
                    header_line = before_date
                elif idx > 0 and (idx - 1) not in used_line_indices and not _ACADEMIC_LINE_RE.search(exp_lines[idx - 1]):
                    header_line = exp_lines[idx - 1]
                    used_line_indices.add(idx - 1)
                else:
                    header_line = "Software Engineer"

                role, company = cls._parse_role_and_company(header_line)
                if company == "Employer" and idx + 1 < len(exp_lines):
                    nxt = exp_lines[idx + 1]
                    if len(nxt) < 70 and not nxt.startswith(("-", "•")) and not _DATE_RANGE_RE.search(nxt):
                        if not _LOCATION_LINE_RE.search(nxt) or "," not in nxt:
                            company = nxt.split("|")[0].strip()[:80]

                bullets = []
                for j in range(idx + 1, min(idx + 8, len(exp_lines))):
                    if _DATE_RANGE_RE.search(exp_lines[j]):
                        break
                    b_line = exp_lines[j].strip()
                    if len(b_line) > 25 and not _LOCATION_LINE_RE.fullmatch(b_line):
                        bullets.append(b_line.lstrip("-•* ").strip())

                dur_m = _INLINE_DURATION_RE.search(line)
                experiences.append(
                    ExperienceItem(
                        company=company,
                        role=role,
                        start_date=start_d,
                        end_date=end_d,
                        duration=dur_m.group(1) if dur_m else "",
                        responsibilities=bullets[:5] or [header_line],
                        technologies=all_skills[:6],
                    )
                )
                used_line_indices.add(idx)
                continue

            # Case 2: Single-line role with explicit duration (e.g. "Senior Engineer (3 years)" or "Backend Intern (6 months)")
            dur_m = _INLINE_DURATION_RE.search(line)
            role_m = _ROLE_WORD_RE.search(line)
            if dur_m and role_m and len(line) < 160:
                before_dur = line[: dur_m.start()].strip(" -–|,()")
                role, company = cls._parse_role_and_company(before_dur or role_m.group(1))
                experiences.append(
                    ExperienceItem(
                        company=company,
                        role=role,
                        start_date="",
                        end_date="",
                        duration=dur_m.group(1),
                        responsibilities=[line],
                        technologies=all_skills[:6],
                    )
                )
                used_line_indices.add(idx)

        return experiences[:8]

    @classmethod
    def extract_candidate_profile(
        cls, raw_text: str, fallback_name: str = ""
    ) -> Tuple[StructuredResume, float, str]:
        """Extract StructuredResume, verified experience years, and normalized location."""
        lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
        sections, has_headers = _split_sections(lines)

        name = cls._extract_name(lines, fallback_name=fallback_name)
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", raw_text)
        email = email_match.group(0) if email_match else ""
        phone_match = re.search(
            r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}", raw_text
        )
        phone = phone_match.group(0).strip() if phone_match else ""

        location = cls._extract_location(sections.get("header") or lines[:10])
        all_skills, by_cat = cls._extract_skills(raw_text)

        # Strictly extract experience ONLY from Experience/Internship section when headers exist.
        # Only fall back to scanning lines for date/duration-backed job lines when a resume has zero section headers.
        experiences: List[ExperienceItem] = []
        if has_headers:
            exp_lines = sections.get("experience", [])
            if exp_lines:
                experiences = cls._extract_experience_from_lines(exp_lines, all_skills)
        else:
            experiences = cls._extract_experience_from_lines(lines, all_skills)

        # Calculate years strictly from extracted job/internship timelines
        temp_resume = StructuredResume(experience=experiences)
        candidate_years = ExperienceMatcher.estimate_candidate_years(temp_resume)

        # Fallback ONLY for unsectioned short snippets that state "X years of experience" without job dates
        if candidate_years == 0.0 and not has_headers and not sections.get("education"):
            yrs_m = re.search(
                r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience",
                raw_text,
                re.IGNORECASE,
            )
            if yrs_m:
                candidate_years = round(float(yrs_m.group(1)), 1)
                experiences.append(
                    ExperienceItem(
                        company="Employer",
                        role="Software Engineer",
                        duration=f"{candidate_years} years",
                        responsibilities=[ln for ln in lines if len(ln) > 20][:3],
                        technologies=all_skills[:6],
                    )
                )

        # Education extraction strictly from education section (or full text if unsectioned)
        edu_text = "\n".join(sections.get("education", [])) if has_headers else raw_text
        education: List[EducationItem] = []
        for match in _DEGREE_RE.finditer(edu_text):
            education.append(
                EducationItem(
                    institution="",
                    degree=match.group(1).strip(),
                    field_of_study=(match.group(2) or "").strip()[:60],
                )
            )
            if len(education) >= 4:
                break

        projects: List[ProjectItem] = []
        summary_lines = sections.get("summary") or [ln for ln in lines[:10] if len(ln) > 40 and "@" not in ln]
        summary = " ".join(summary_lines[:2])[:350] or (
            f"Candidate profile covering {', '.join(all_skills[:5]) or 'engineering skills'}."
        )

        profile = StructuredResume(
            name=name,
            email=email,
            phone=phone,
            location=location,
            summary=summary,
            skills=all_skills,
            technical_skills=all_skills,
            programming_languages=by_cat["Programming Languages"],
            frameworks=by_cat["Frameworks"],
            databases=by_cat["Databases"],
            cloud=by_cat["Cloud"] + by_cat["DevOps"],
            tools=by_cat["Tools"],
            experience=experiences,
            education=education,
            projects=projects,
        )
        return profile, candidate_years, location


def classify_match(
    overall_score: float,
    missing_required_count: int = 0,
    hard_filter_passed: bool = True,
) -> str:
    """Deterministic match classification badge."""
    if not hard_filter_passed and overall_score < 60.0:
        return "WEAK_MATCH"
    if overall_score >= 82.0 and missing_required_count == 0 and hard_filter_passed:
        return "STRONG_MATCH"
    if overall_score >= 65.0 and hard_filter_passed:
        return "GOOD_MATCH"
    if overall_score >= 45.0:
        return "PARTIAL_MATCH"
    return "WEAK_MATCH"
