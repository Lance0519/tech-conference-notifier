from __future__ import annotations

import pytest
from tech_conf_notifier.classifier import EventClassifier, CATEGORY_LEXICON
from tech_conf_notifier.models import MANDATORY_CATEGORIES, TARGET_AUDIENCE_PERSONAS


class TestEventClassifier:
    """Comprehensive test suite for the 16 IT/CS categories, audience detection, disambiguation, and rejection filter."""

    @pytest.mark.parametrize("category,keywords", [
        ("Computer Science", ["Theoretical Computer Science and Discrete Mathematics Symposium", "Formal methods and computational complexity"]),
        ("Information Technology", ["Enterprise IT and Systems Administration Summit", "Datacenter infrastructure and ITSM virtualization"]),
        ("Software Engineering", ["International Conference on Software Engineering", "Clean Code, Design Patterns, and Microservices Architecture"]),
        ("Artificial Intelligence and Machine Learning", ["Global Generative AI & Deep Learning Summit", "Neural networks, LLM, and reinforcement learning"]),
        ("Data Science and Analytics", ["Big Data Science and Analytics Conference", "Data pipeline, ETL, and predictive analytics expo"]),
        ("Cybersecurity", ["Defensive Cybersecurity and Ethical Hacking Forum", "Penetration testing, zero trust, and vulnerability analysis"]),
        ("Networking and Telecommunications", ["NextGen 5G Telecommunications and Routing Summit", "BGP, OSPF, and optical networking symposium"]),
        ("Cloud Computing and DevOps", ["Cloud Native DevOps and Kubernetes Gathering", "AWS, Terraform, Docker, and SRE summit"]),
        ("Web and Mobile Development", ["Modern Web & Mobile Development Conference", "React, Flutter, TypeScript, and Android frontend summit"]),
        ("Game Development", ["Annual Game Development & Unreal Engine Expo", "Godot, Vulkan shaders, and gameplay programming"]),
        ("Robotics and Internet of Things", ["Robotics and Internet of Things Convention", "Embedded systems, ROS, and Arduino edge computing"]),
        ("Information Systems", ["Enterprise Information Systems and ERP Architecture", "Management information systems and TOGAF framework"]),
        ("Database Management", ["Distributed Database Management Summit", "PostgreSQL, NoSQL, query optimization, and Redis"]),
        ("Computer Engineering", ["Microprocessor Design and Computer Engineering Forum", "VLSI, RISC-V architecture, and FPGA digital logic"]),
        ("Emerging Technologies", ["Quantum Computing and Emerging Technologies Summit", "Smart contracts, decentralized algorithms, and neuromorphic computing"]),
        ("Technology Entrepreneurship and Innovation", ["Deep Tech Startup and Technology Entrepreneurship Forum", "Tech incubator, software product management, and venture capital"]),
    ])
    def test_mandatory_16_categories_classification(self, category: str, keywords: list[str]):
        """Verifies each of the 16 mandatory categories is correctly detected."""
        for text in keywords:
            cat, secondary, confidence = EventClassifier.classify(name=text, description=text)
            assert cat == category, f"Expected '{category}' for '{text}', got '{cat}'"
            assert 0.50 <= confidence <= 0.99

    def test_all_16_categories_represented_in_lexicon(self):
        """Ensures the classifier lexicon exactly covers all 16 mandatory categories."""
        assert len(MANDATORY_CATEGORIES) == 16
        for cat in MANDATORY_CATEGORIES:
            assert cat in CATEGORY_LEXICON, f"Missing {cat} in CATEGORY_LEXICON"

    def test_title_weighting_over_description(self):
        """Title occurrences should outweigh description occurrences (3x)."""
        # Title is Cybersecurity, Description mentions Cloud Computing twice
        title = "Cybersecurity Leadership Summit"
        desc = "Discussing cloud computing infrastructure and cloud computing workloads."
        primary, _, _ = EventClassifier.classify(name=title, description=desc)
        assert primary == "Cybersecurity"

    def test_target_audience_detection(self):
        # Student audience
        s_text = "University Hackathon and Student Coding Bootcamp"
        audiences = EventClassifier.detect_audiences(s_text)
        assert "Students" in audiences

        # Developer audience
        d_text = "Hands-on Developer Workshop with SDK Tutorials"
        audiences = EventClassifier.detect_audiences(d_text)
        assert "Developers" in audiences

        # Researcher audience
        r_text = "Call for Papers: IEEE Peer-Reviewed Research Proceedings"
        audiences = EventClassifier.detect_audiences(r_text)
        assert "Researchers" in audiences

        # Executive audience
        e_text = "CIO & CTO Strategy Keynote on Enterprise ROI"
        audiences = EventClassifier.detect_audiences(e_text)
        assert "IT Executives" in audiences

        # Fallback to Developers and General Public
        fallback_audiences = EventClassifier.detect_audiences("Annual Gathering")
        assert "Developers" in fallback_audiences
        assert "General Public" in fallback_audiences

    def test_polysemic_disambiguation_python(self):
        # Valid tech context
        is_tech, reason = EventClassifier.is_tech_event("Python Web Developer Summit", "Django and machine learning")
        assert is_tech is True
        assert reason is None

        # Animal / snake context rejected
        is_tech, reason = EventClassifier.is_tech_event("Burmese Python Snake Breeders Expo", "Reptile pet care")
        assert is_tech is False
        assert "non-tech context" in reason

        # Short unanchored title rejected
        is_tech, reason = EventClassifier.is_tech_event("Python Festival", "Community gathering")
        assert is_tech is False
        assert "contextual anchor" in reason

    def test_polysemic_disambiguation_rust(self):
        # Tech Rust
        is_tech, _ = EventClassifier.is_tech_event("Rust Systems Programming Conference", "Cargo crates and memory safety")
        assert is_tech is True

        # Metal Rust
        is_tech, reason = EventClassifier.is_tech_event("Auto Rust and Corrosion Restoration", "Metal paint treatments")
        assert is_tech is False
        assert "non-tech context" in reason

    def test_polysemic_disambiguation_java(self):
        # Tech Java
        is_tech, _ = EventClassifier.is_tech_event("Java Spring Framework Summit", "JVM microservices and bytecode")
        assert is_tech is True

        # Coffee Java
        is_tech, reason = EventClassifier.is_tech_event("Artisan Java Coffee Roast Festival", "Espresso beans tasting cafe")
        assert is_tech is False
        assert "non-tech context" in reason

    def test_polysemic_disambiguation_go(self):
        # Tech Go
        is_tech, _ = EventClassifier.is_tech_event("Go Cloud Native Conference", "Golang microservices and goroutine optimization")
        assert is_tech is True

        # Board Game Go
        is_tech, reason = EventClassifier.is_tech_event("Go Board Game Championship", "Baduk strategies and tournament")
        assert is_tech is False
        assert "non-tech context" in reason

    def test_polysemic_disambiguation_security(self):
        # Cyber Security
        is_tech, _ = EventClassifier.is_tech_event("Enterprise Security & Infosec Expo", "Vulnerability management and firewalls")
        assert is_tech is True

        # Physical Security Guard
        is_tech, reason = EventClassifier.is_tech_event("Nightclub Security Guard and Bouncer Training", "Patrol tactics")
        assert is_tech is False
        assert "non-tech context" in reason

    def test_polysemic_disambiguation_networking(self):
        # Computer Networking
        is_tech, _ = EventClassifier.is_tech_event("Cisco Optical Networking Summit", "BGP routing and telecom protocols")
        assert is_tech is True

        # Social / Cocktail Networking
        is_tech, reason = EventClassifier.is_tech_event("Business Networking and Singles Mixer", "Cocktails and speed dating")
        assert is_tech is False
        assert "non-tech context" in reason

    @pytest.mark.parametrize("name,desc", [
        ("National Dental & Dentistry Congress", "Orthodontic clinical updates"),
        ("Manila Real Estate & Realtor Expo", "Property investment and home buying"),
        ("Cosmetic Surgery and Aesthetic Medicine Forum", "Plastic surgery and dermatology clinic treatments"),
        ("Spiritual Wellness & Reiki Healing Retreat", "Weight loss clinic and horoscope readings"),
        ("Grand Wedding Expo & Bridal Fashion Runway", "Luxury jewelry and wedding gowns"),
        ("Poultry Breeding & Livestock Agriculture Expo", "Tractors and veterinary clinic medicine"),
        ("Day Trading Forex & Binary Options Wealth Seminar", "Get rich quick and mlm network marketing"),
    ])
    def test_strict_rejection_of_non_tech_events(self, name: str, desc: str):
        """Strict 100% rejection rate on non-tech events across all forbidden domains."""
        is_tech, reason = EventClassifier.is_tech_event(name, desc)
        assert is_tech is False, f"Event '{name}' should have been rejected as non-tech"
        assert "blacklist" in reason.lower()
