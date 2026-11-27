import re
from typing import Dict, Tuple

# Comprehensive skill aliases mapping variant terms to a canonical name and category
SKILL_ALIASES: Dict[str, Tuple[str, str]] = {
    # Databases
    "postgres": ("PostgreSQL", "Databases"),
    "postgresql": ("PostgreSQL", "Databases"),
    "postgresql db": ("PostgreSQL", "Databases"),
    "psql": ("PostgreSQL", "Databases"),
    "mongo": ("MongoDB", "Databases"),
    "mongodb": ("MongoDB", "Databases"),
    "redis": ("Redis", "Databases"),
    "mysql": ("MySQL", "Databases"),
    "sqlite": ("SQLite", "Databases"),
    "cassandra": ("Cassandra", "Databases"),
    "dynamodb": ("DynamoDB", "Databases"),
    "elastic": ("Elasticsearch", "Databases"),
    "elasticsearch": ("Elasticsearch", "Databases"),
    
    # Programming Languages
    "python": ("Python", "Programming Languages"),
    "py": ("Python", "Programming Languages"),
    "js": ("JavaScript", "Programming Languages"),
    "javascript": ("JavaScript", "Programming Languages"),
    "ts": ("TypeScript", "Programming Languages"),
    "typescript": ("TypeScript", "Programming Languages"),
    "golang": ("Go", "Programming Languages"),
    "go": ("Go", "Programming Languages"),
    "rust": ("Rust", "Programming Languages"),
    "java": ("Java", "Programming Languages"),
    "c++": ("C++", "Programming Languages"),
    "cpp": ("C++", "Programming Languages"),
    "c#": ("C#", "Programming Languages"),
    "csharp": ("C#", "Programming Languages"),
    "ruby": ("Ruby", "Programming Languages"),
    "php": ("PHP", "Programming Languages"),
    "sql": ("SQL", "Programming Languages"),

    # Frameworks
    "fastapi": ("FastAPI", "Frameworks"),
    "fast-api": ("FastAPI", "Frameworks"),
    "django": ("Django", "Frameworks"),
    "flask": ("Flask", "Frameworks"),
    "react": ("React", "Frameworks"),
    "reactjs": ("React", "Frameworks"),
    "react.js": ("React", "Frameworks"),
    "next": ("Next.js", "Frameworks"),
    "nextjs": ("Next.js", "Frameworks"),
    "next.js": ("Next.js", "Frameworks"),
    "node": ("Node.js", "Frameworks"),
    "nodejs": ("Node.js", "Frameworks"),
    "node.js": ("Node.js", "Frameworks"),
    "express": ("Express", "Frameworks"),
    "expressjs": ("Express", "Frameworks"),
    "vue": ("Vue.js", "Frameworks"),
    "vuejs": ("Vue.js", "Frameworks"),
    "angular": ("Angular", "Frameworks"),
    "tailwind": ("Tailwind CSS", "Frameworks"),
    "tailwindcss": ("Tailwind CSS", "Frameworks"),
    "spring": ("Spring Boot", "Frameworks"),
    "spring boot": ("Spring Boot", "Frameworks"),
    "pytorch": ("PyTorch", "AI/ML"),
    "tensorflow": ("TensorFlow", "AI/ML"),
    "langchain": ("LangChain", "AI/ML"),

    # Cloud & DevOps
    "aws": ("AWS", "Cloud"),
    "amazon web services": ("AWS", "Cloud"),
    "gcp": ("Google Cloud", "Cloud"),
    "google cloud": ("Google Cloud", "Cloud"),
    "google cloud platform": ("Google Cloud", "Cloud"),
    "azure": ("Azure", "Cloud"),
    "docker": ("Docker", "DevOps"),
    "k8s": ("Kubernetes", "DevOps"),
    "kubernetes": ("Kubernetes", "DevOps"),
    "terraform": ("Terraform", "DevOps"),
    "ci/cd": ("CI/CD", "DevOps"),
    "github actions": ("GitHub Actions", "DevOps"),
    "git": ("Git", "Tools"),
    "linux": ("Linux", "Tools"),
}


class SkillNormalizer:
    @staticmethod
    def clean_text(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s\+\#\.\/\-]", "", text)
        return text

    @classmethod
    def normalize_skill(cls, skill: str) -> Tuple[str, str]:
        """
        Returns (canonical_name, category).
        If not in dictionary, returns (formatted_original, 'General').
        """
        cleaned = cls.clean_text(skill)
        if cleaned in SKILL_ALIASES:
            return SKILL_ALIASES[cleaned]

        # Check partial prefix/suffix match
        for key, (canonical, category) in SKILL_ALIASES.items():
            if cleaned == key or f" {key} " in f" {cleaned} ":
                return canonical, category

        # Default formatting
        title_cased = skill.strip().title() if len(skill) > 3 else skill.strip().upper()
        return title_cased, "General"

