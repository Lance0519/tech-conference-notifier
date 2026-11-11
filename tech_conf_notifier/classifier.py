from __future__ import annotations

import re
from typing import List, Tuple, Dict, Set, Optional
from tech_conf_notifier.models import MANDATORY_CATEGORIES, TARGET_AUDIENCE_PERSONAS

# Strict Non-Tech Blacklist Patterns
NON_TECH_BLACKLIST_REGEX = re.compile(
    r"\b("
    r"dental|dentistry|orthodontic|medical clinical|pediatric|oncology|chiropractic|"
    r"real estate|realtor|property investment|mortgage brokerage|home buying|"
    r"cosmetic surgery|plastic surgery|dermatology clinic|aesthetic medicine|"
    r"weight loss clinic|spiritual wellness|reiki healing|astrology|horoscope|"
    r"wedding expo|bridal show|fashion runway|luxury jewelry auction|"
    r"livestock|poultry breeding|agriculture tractor|veterinary clinic|"
    r"day trading forex|binary options|mlm network marketing|get rich quick"
    r")\b",
    re.IGNORECASE
)

# Mandatory 16-Category Keyword Lexicon with Weighted Terms
CATEGORY_LEXICON: Dict[str, Dict[str, Any]] = {
    "Computer Science": {
        "core": ["computer science", "theoretical computer science", "discrete mathematics", "computational complexity", "automata", "formal methods", "lambda calculus", "turing", "graph theory algorithms", "computational geometry"],
        "weight": 1.0
    },
    "Information Technology": {
        "core": ["information technology", "enterprise it", "systems administration", "sysadmin", "itsm", "itil", "helpdesk automation", "virtualization", "disaster recovery", "datacenter infrastructure", "it service management"],
        "weight": 1.0
    },
    "Software Engineering": {
        "core": ["software engineering", "software architecture", "clean code", "design patterns", "microservices", "testing", "quality assurance", "ci/cd", "agile", "scrum", "refactoring", "static analysis", "unit testing", "icse", "fse"],
        "weight": 1.0
    },
    "Artificial Intelligence and Machine Learning": {
        "core": ["artificial intelligence", "machine learning", "deep learning", "neural network", "llm", "large language model", "generative ai", "nlp", "computer vision", "reinforcement learning", "pytorch", "tensorflow", "transformer", "neurips", "icml", "cvpr"],
        "weight": 1.1
    },
    "Data Science and Analytics": {
        "core": ["data science", "data analytics", "big data", "data pipeline", "business intelligence", "pandas", "apache spark", "hadoop", "predictive analytics", "etl", "data mining", "data warehouse", "snowflake", "databricks"],
        "weight": 1.0
    },
    "Cybersecurity": {
        "core": ["cybersecurity", "infosec", "information security", "penetration testing", "ethical hacking", "vulnerability", "cryptography", "zero trust", "malware", "soc", "siem", "firewall", "def con", "black hat", "owasp", "cve", "devsecops"],
        "weight": 1.1
    },
    "Networking and Telecommunications": {
        "core": ["networking", "telecommunications", "5g", "6g", "sdn", "bgp", "ospf", "tcp/ip", "optical network", "wi-fi", "voip", "routing", "switching", "sigcomm", "infocom", "cisco", "cellular network"],
        "weight": 1.0
    },
    "Cloud Computing and DevOps": {
        "core": ["cloud computing", "devops", "aws", "azure", "google cloud", "gcp", "kubernetes", "k8s", "docker", "containers", "terraform", "ansible", "serverless", "sre", "site reliability", "kubecon", "cloud native"],
        "weight": 1.1
    },
    "Web and Mobile Development": {
        "core": ["web development", "mobile development", "react", "vue", "angular", "svelte", "frontend", "backend", "ios", "swift", "android", "kotlin", "flutter", "react native", "javascript", "typescript", "node.js", "django", "fastapi"],
        "weight": 1.0
    },
    "Game Development": {
        "core": ["game development", "game engine", "unreal engine", "unity3d", "godot", "vulkan", "directx", "shaders", "game physics", "gameplay programming", "gamedev", "rendering engine", "spatial computing", "vr gaming"],
        "weight": 1.0
    },
    "Robotics and Internet of Things": {
        "core": ["robotics", "internet of things", "iot", "embedded systems", "microcontroller", "esp32", "stm32", "arduino", "raspberry pi", "ros", "robot operating system", "edge computing", "sensors", "iiot", "autonomous vehicles"],
        "weight": 1.0
    },
    "Information Systems": {
        "core": ["information systems", "management information systems", "mis", "erp", "sap", "crm", "enterprise architecture", "togaf", "data governance", "hipaa", "gdpr", "fintech systems", "core banking"],
        "weight": 1.0
    },
    "Database Management": {
        "core": ["database", "dbms", "postgresql", "postgres", "mysql", "nosql", "mongodb", "redis", "distributed sql", "cockroachdb", "vector database", "query optimization", "sigmod", "vldb", "indexing"],
        "weight": 1.0
    },
    "Computer Engineering": {
        "core": ["computer engineering", "hardware", "vlsi", "fpga", "asic", "risc-v", "arm architecture", "semiconductor", "microprocessor", "chip design", "digital logic", "hardware-software codesign"],
        "weight": 1.0
    },
    "Emerging Technologies": {
        "core": ["emerging technologies", "quantum computing", "quantum algorithm", "neuromorphic", "web3", "blockchain", "decentralized", "smart contracts", "bci", "brain computer interface", "synthetic biology computing"],
        "weight": 1.0
    },
    "Technology Entrepreneurship and Innovation": {
        "core": ["technology entrepreneurship", "tech startup", "deep tech", "venture capital", "open source commercialization", "software product management", "tech incubator", "innovation summit", "hackathon"],
        "weight": 1.0
    }
}

# Polysemic word disambiguation requirements (Contextual Anchors)
DISAMBIGUATION_RULES: Dict[str, Dict[str, Any]] = {
    "python": {
        "requires_one_of": ["programming", "code", "software", "developer", "pycon", "django", "flask", "pypi", "data", "script", "interpreter", "machine learning", "ai", "pip"],
        "reject_if_matches": ["snake", "reptile", "zoo", "ball python", "pet shop", "circus", "comedy"]
    },
    "rust": {
        "requires_one_of": ["programming", "code", "cargo", "crates", "compiler", "memory safety", "systems", "concurrency", "developer", "rustconf"],
        "reject_if_matches": ["corrosion", "metal restoration", "paint", "chassis", "car rust", "oxidation"]
    },
    "java": {
        "requires_one_of": ["jvm", "spring", "quarkus", "oracle", "bytecode", "kotlin", "jakarta", "maven", "gradle", "programming", "software"],
        "reject_if_matches": ["coffee", "roast", "espresso", "beans", "cafe", "island"]
    },
    "go": {
        "requires_one_of": ["golang", "goroutine", "compiler", "google", "backend", "cloud native", "docker", "kubernetes", "programming"],
        "reject_if_matches": ["board game", "baduk", "weiqi", "kart", "go-kart"]
    },
    "security": {
        "requires_one_of": ["cyber", "infosec", "vulnerability", "cve", "malware", "pentesting", "hacking", "crypto", "firewall", "zero trust", "soc", "siem"],
        "reject_if_matches": ["security guard", "bouncer", "locksmith", "physical security", "patrol", "alarm installation"]
    },
    "networking": {
        "requires_one_of": ["cisco", "juniper", "bgp", "ospf", "tcp/ip", "sdn", "packets", "bandwidth", "switch", "router", "telecom", "protocols"],
        "reject_if_matches": ["cocktail", "speed dating", "business cards", "singles mixer", "pitch your startup"]
    }
}


class EventClassifier:
    """
    Intelligent Multi-Label Classification & Filtering Engine for the 16 IT/CS Categories.
    Ensures zero false-positives and accurate target audience tagging.
    """

    @classmethod
    def is_tech_event(cls, name: str, description: str, tags: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
        """
        Gatekeeper: Verifies that an event is genuinely relevant to IT, CS, or Technology.
        Returns (is_tech, exclusion_reason).
        """
        full_text = f"{name} {description} {' '.join(tags or [])}".lower()

        # 1. Check Non-Tech Blacklist
        blacklisted = NON_TECH_BLACKLIST_REGEX.search(full_text)
        if blacklisted:
            return False, f"Matches non-tech blacklist domain: '{blacklisted.group(0)}'"

        # 2. Check Polysemic Disambiguation
        for keyword, rule in DISAMBIGUATION_RULES.items():
            if re.search(r"\b" + re.escape(keyword) + r"\b", full_text):
                # Check rejection terms
                if any(re.search(r"\b" + re.escape(neg) + r"\b", full_text) for neg in rule["reject_if_matches"]):
                    return False, f"Polysemic term '{keyword}' matched non-tech context"
                
                # If the title strictly relies on this word, check if technical anchor exists
                anchored = any(re.search(r"\b" + re.escape(anc) + r"\b", full_text) for anc in rule["requires_one_of"])
                if not anchored and len(name.split()) <= 4:
                    return False, f"Term '{keyword}' lacks mandatory technical contextual anchor"

        return True, None

    @classmethod
    def classify(cls, name: str, description: str = "", tags: Optional[List[str]] = None) -> Tuple[str, List[str], float]:
        """
        Classifies event into the 16 mandatory categories.
        Returns (primary_category, secondary_categories, confidence_score).
        """
        full_text = f"{name} {description} {' '.join(tags or [])}".lower()
        scores: Dict[str, float] = {}

        for cat, config in CATEGORY_LEXICON.items():
            cat_score = 0.0
            weight = config["weight"]
            for term in config["core"]:
                # Word boundary match
                pattern = r"\b" + re.escape(term) + r"\b"
                matches = len(re.findall(pattern, full_text))
                if matches > 0:
                    # Title matches weigh 3x higher than description
                    title_matches = len(re.findall(pattern, name.lower()))
                    cat_score += (title_matches * 3.0 + (matches - title_matches) * 1.0) * weight
            
            if cat_score > 0:
                scores[cat] = cat_score

        if not scores:
            # Fallback based on tech heuristics
            if any(w in full_text for w in ["research", "ieee", "acm", "theory", "algorithm", "symposium"]):
                return "Computer Science", [], 0.5
            return "Information Technology", [], 0.5

        sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary_category = sorted_cats[0][0]
        max_score = sorted_cats[0][1]

        # Secondary categories (score >= 40% of primary score)
        secondary = [c for c, s in sorted_cats[1:] if s >= (max_score * 0.40)][:3]

        # Confidence bounded between 0.5 and 0.99
        confidence = min(0.99, 0.50 + (max_score / 15.0))
        return primary_category, secondary, round(confidence, 2)

    @classmethod
    def detect_audiences(cls, name: str, description: str = "") -> List[str]:
        """Detects target audience personas."""
        text = f"{name} {description}".lower()
        audiences = set()

        if any(w in text for w in ["hackathon", "student", "scholarship", "beginner", "undergraduate", "bootcamp"]):
            audiences.add("Students")
        if any(w in text for w in ["code", "developer", "hands-on", "workshop", "api", "sdk", "dev", "tutorial", "github"]):
            audiences.add("Developers")
        if any(w in text for w in ["call for papers", "cfp", "proceedings", "peer-reviewed", "research", "ieee", "acm", "springer", "arxiv"]):
            audiences.add("Researchers")
        if any(w in text for w in ["c-level", "cio", "cto", "ciso", "executive", "roi", "governance", "enterprise leadership", "keynote strategy"]):
            audiences.add("IT Executives")

        if not audiences:
            audiences.add("Developers")
            audiences.add("General Public")

        return [p for p in TARGET_AUDIENCE_PERSONAS if p in audiences]
