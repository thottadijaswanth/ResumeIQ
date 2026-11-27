import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from backend.app.schemas.analysis import ExperienceGap
from backend.app.schemas.job import StructuredJob
from backend.app.schemas.resume import StructuredResume

_MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def _current_year_month() -> Tuple[int, int]:
    now = datetime.now(timezone.utc)
    return now.year, now.month


def _parse_year_month(date_str: str, *, is_end: bool = False) -> Optional[Tuple[int, int]]:
    """
    Parse dates like 'Jul 2025', 'July 2025', '07/2025', '2025-07', '2025', or 'Present'.
    Returns (year, month) or None if unparseable.
    """
    if not date_str:
        return None
    cleaned = date_str.strip()
    lower = cleaned.lower()

    if any(tok in lower for tok in ("present", "current", "now", "till date", "ongoing")):
        return _current_year_month()

    # Month name + Year (e.g. "Jul 2025", "January, 2024")
    m_name = re.search(r"\b([a-z]{3,9})[.,\s\-]+((?:19|20)\d{2})\b", lower)
    if m_name and m_name.group(1) in _MONTH_MAP:
        return int(m_name.group(2)), _MONTH_MAP[m_name.group(1)]

    # Numeric MM/YYYY or MM-YYYY
    m_num = re.search(r"\b(0?[1-9]|1[0-2])[/\-]((?:19|20)\d{2})\b", lower)
    if m_num:
        return int(m_num.group(2)), int(m_num.group(1))

    # Numeric YYYY-MM or YYYY/MM
    m_iso = re.search(r"\b((?:19|20)\d{2})[/\-](0?[1-9]|1[0-2])\b", lower)
    if m_iso:
        return int(m_iso.group(1)), int(m_iso.group(2))

    # Year only (YYYY)
    m_yr = re.search(r"\b((?:19|20)\d{2})\b", lower)
    if m_yr:
        year = int(m_yr.group(1))
        return year, (12 if is_end else 1)

    return None


def _parse_duration_months(duration_str: str) -> Optional[int]:
    if not duration_str:
        return None
    lower = duration_str.lower()
    yr_match = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b", lower)
    mo_match = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:months?|mos?)\b", lower)
    if yr_match or mo_match:
        months = 0.0
        if yr_match:
            months += float(yr_match.group(1)) * 12.0
        if mo_match:
            months += float(mo_match.group(1))
        return max(1, round(months))
    return None


class ExperienceMatcher:
    @staticmethod
    def estimate_candidate_years(resume: StructuredResume) -> float:
        """
        Calculate total candidate years from verified work/internship experience timelines.
        Merges overlapping date intervals so concurrent roles are not double-counted,
        and never invents default years for undated or missing experience.
        """
        intervals: List[Tuple[int, int]] = []
        fallback_months = 0

        for exp in resume.experience:
            start_ym = _parse_year_month(exp.start_date, is_end=False)
            end_ym = _parse_year_month(exp.end_date, is_end=True)

            if start_ym and end_ym:
                s_idx = start_ym[0] * 12 + (start_ym[1] - 1)
                e_idx = end_ym[0] * 12 + (end_ym[1] - 1)
                if e_idx >= s_idx:
                    # Inclusive month count (e.g. Jul 2025 -> Nov 2026 = 17 months = 1.4 yrs)
                    intervals.append((s_idx, e_idx + 1))
                    continue

            dur_months = _parse_duration_months(exp.duration)
            if dur_months:
                fallback_months += dur_months

        total_months = fallback_months
        if intervals:
            intervals.sort(key=lambda pair: pair[0])
            merged: List[Tuple[int, int]] = [intervals[0]]
            for s, e in intervals[1:]:
                prev_s, prev_e = merged[-1]
                if s <= prev_e:
                    merged[-1] = (prev_s, max(prev_e, e))
                else:
                    merged.append((s, e))
            total_months += sum(e - s for s, e in merged)

        return round(total_months / 12.0, 1)

    @classmethod
    def match_experience(
        cls,
        resume: StructuredResume,
        job: StructuredJob,
    ) -> Tuple[float, ExperienceGap]:
        """
        Compare verified industrial/internship timeline years and role level.
        Returns (experience_score: 0-100, experience_gap: ExperienceGap)
        """
        candidate_years = cls.estimate_candidate_years(resume)
        required_years = (
            job.min_experience
            if job.min_experience is not None
            else (job.years_of_experience if job.years_of_experience is not None else 2.0)
        )

        gaps = []
        if required_years > 0 and candidate_years <= 0.0:
            gaps.append(
                f"No verified work or internship experience timeline found against {required_years} years requested."
            )
            score = 5.0
        elif required_years > 0 and candidate_years < required_years:
            gap_diff = required_years - candidate_years
            gaps.append(
                f"Candidate has {candidate_years} years of verified work/internship timeline vs {required_years} years requested ({gap_diff:.1f} yr gap)."
            )
            ratio = candidate_years / required_years
            score = max(10.0, min(95.0, ratio * 85.0))
        else:
            score = 100.0

        # Seniority level comparison
        title_lower = job.job_title.lower()
        if any(w in title_lower for w in ["lead", "staff", "principal", "director"]):
            target_level = "Lead / Principal"
        elif "senior" in title_lower:
            target_level = "Senior"
        elif any(w in title_lower for w in ["junior", "associate", "entry"]):
            target_level = "Entry / Junior"
        else:
            target_level = "Mid-Level"

        candidate_has_senior = any(
            any(w in exp.role.lower() for w in ["senior", "lead", "staff", "architect", "head"])
            for exp in resume.experience
        )

        if "Senior" in target_level and not candidate_has_senior and candidate_years < 4.0:
            gaps.append("Target role is Senior level, but candidate work history does not reflect senior experience.")
            score = max(5.0, score - 15.0)

        details = (
            f"Candidate has {candidate_years} years of verified work/internship experience against "
            f"target requirement of {required_years} years for a {target_level} role."
        )

        return round(score, 2), ExperienceGap(
            required_years=required_years,
            candidate_years=candidate_years,
            role_level_match=target_level,
            details=details,
            gaps=gaps,
        )
