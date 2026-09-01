"""
Synthetic CV Profile Generator with Archetype Controls

Generates realistic candidate profiles categorized into three archetypes:
- STRONG: Clearly qualified candidates (expected score 80-95)
- NORMAL: Mixed qualifications (expected score 50-75)
- WEAK: Clearly underqualified (expected score 15-40)

Usage:
    python scripts/generate_profiles.py [--count STRONG NORMAL WEAK RANDOM] [--output data/synthetic/profiles.json]
"""

import json
import random
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

# ============================================================
# SKILL POOLS (organized by domain)
# ============================================================

SKILL_POOLS = {
    "backend": {
        "languages": ["Python", "Java", "Go", "Rust", "C#", "Ruby", "PHP", "Kotlin", "Scala", "Elixir"],
        "frameworks": ["FastAPI", "Django", "Flask", "Spring Boot", "Express.js", "NestJS", "Gin", "Actix Web", "Rails", "Laravel"],
        "databases": ["PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "DynamoDB", "Cassandra", "Neo4j", "SQLite", "InfluxDB"],
        "infrastructure": ["Docker", "Kubernetes", "AWS", "GCP", "Azure", "CI/CD", "Terraform", "Jenkins", "GitHub Actions", "Nginx"],
        "messaging": ["RabbitMQ", "Kafka", "Redis Pub/Sub", "AWS SQS", "gRPC"],
    },
    "data_science": {
        "languages": ["Python", "R", "SQL", "Julia", "Scala"],
        "ml_frameworks": ["TensorFlow", "PyTorch", "scikit-learn", "XGBoost", "LightGBM", "Keras", "JAX", "Hugging Face Transformers"],
        "data_tools": ["Pandas", "NumPy", "Matplotlib", "Seaborn", "Plotly", "Jupyter", "Apache Spark", "Dask", "Polars"],
        "databases": ["PostgreSQL", "MySQL", "BigQuery", "Snowflake", "Redshift", "MongoDB", "ClickHouse"],
        "cloud": ["AWS SageMaker", "GCP Vertex AI", "Azure ML", "MLflow", "Weights & Biases", "Docker"],
    },
    "frontend": {
        "languages": ["JavaScript", "TypeScript", "HTML", "CSS", "Swift", "Kotlin"],
        "frameworks": ["React", "Vue.js", "Angular", "Next.js", "Svelte", "Remix", "Nuxt.js", "Astro"],
        "styling": ["Tailwind CSS", "SASS/SCSS", "CSS Modules", "Styled Components", "Material UI", "Chakra UI", "Ant Design"],
        "tools": ["Webpack", "Vite", "ESLint", "Prettier", "Storybook", "Figma", "Git", "npm/yarn/pnpm"],
        "testing": ["Jest", "Cypress", "Playwright", "React Testing Library", "Vitest"],
    },
}

# ============================================================
# EXPERIENCE TEMPLATES
# ============================================================

EXPERIENCE_TEMPLATES = {
    "backend": [
        {"title": "Junior Backend Developer", "min_years": 0, "max_years": 2},
        {"title": "Backend Developer", "min_years": 2, "max_years": 5},
        {"title": "Senior Backend Developer", "min_years": 5, "max_years": 10},
        {"title": "Lead Backend Engineer", "min_years": 7, "max_years": 15},
        {"title": "Staff Engineer", "min_years": 10, "max_years": 20},
        {"title": "Backend Developer Intern", "min_years": 0, "max_years": 1},
        {"title": "Freelance Backend Developer", "min_years": 1, "max_years": 8},
    ],
    "data_science": [
        {"title": "Data Analyst", "min_years": 0, "max_years": 3},
        {"title": "Junior Data Scientist", "min_years": 1, "max_years": 3},
        {"title": "Data Scientist", "min_years": 3, "max_years": 7},
        {"title": "Senior Data Scientist", "min_years": 5, "max_years": 12},
        {"title": "ML Engineer", "min_years": 3, "max_years": 10},
        {"title": "Research Scientist", "min_years": 5, "max_years": 15},
        {"title": "Data Science Intern", "min_years": 0, "max_years": 1},
    ],
    "frontend": [
        {"title": "Junior Frontend Developer", "min_years": 0, "max_years": 2},
        {"title": "Frontend Developer", "min_years": 2, "max_years": 5},
        {"title": "Senior Frontend Developer", "min_years": 5, "max_years": 10},
        {"title": "Lead Frontend Engineer", "min_years": 7, "max_years": 15},
        {"title": "UI/UX Developer", "min_years": 2, "max_years": 8},
        {"title": "Frontend Developer Intern", "min_years": 0, "max_years": 1},
        {"title": "Freelance Web Developer", "min_years": 1, "max_years": 8},
    ],
}

# ============================================================
# EDUCATION TEMPLATES
# ============================================================

EDUCATION_LEVELS = {
    "high_school": {"level": 1, "degree": "High School Diploma", "field_options": []},
    "associate": {"level": 2, "degree": "Associate's Degree", "field_options": ["Computer Science", "Information Technology", "Engineering"]},
    "bachelor": {"level": 3, "degree": "Bachelor of Science", "field_options": ["Computer Science", "Software Engineering", "Information Technology", "Data Science", "Mathematics", "Electrical Engineering"]},
    "master": {"level": 4, "degree": "Master of Science", "field_options": ["Computer Science", "Software Engineering", "Data Science", "Artificial Intelligence", "Machine Learning", "Cybersecurity"]},
    "phd": {"level": 5, "degree": "PhD", "field_options": ["Computer Science", "Artificial Intelligence", "Machine Learning", "Computational Linguistics"]},
}

UNIVERSITIES = [
    "MIT", "Stanford University", "Carnegie Mellon University", "UC Berkeley",
    "Georgia Institute of Technology", "University of Michigan", "University of Washington",
    "Columbia University", "Cornell University", "Princeton University",
    "University of Illinois Urbana-Champaign", "Purdue University", "University of Texas at Austin",
    "University of Southern California", "University of California Los Angeles",
    "University of Pennsylvania", "Duke University", "Northwestern University",
    "University of Wisconsin-Madison", "Ohio State University",
    "University of Maryland", "University of Virginia", "Boston University",
    "New York University", "University of Florida",
    "State University of New York", "University of Minnesota",
    "University of Colorado Boulder", "University of Arizona",
    "Arizona State University", "San Jose State University",
    "University of California San Diego", "University of California Davis",
    "Johns Hopkins University", "Rice University", "Vanderbilt University",
    "University of North Carolina at Chapel Hill", "University of Pittsburgh",
    "Iowa State University", "University of Iowa",
    "Less Known State University", "Community College of Denver",
    "Online University (Coursera)", "Bootcamp Graduate (App Academy)",
]

COMPANIES = FAKE_COMPANIES = [
    "TechCorp", "DataFlow Inc", "CloudNine Solutions", "ByteForge",
    "PixelWorks", "CodeHive", "NetSphere", "InnoSoft", "CyberLink",
    "QuantumByte", "Stackify", "AgileWorks", "DevOps Pro", "AI Dynamics",
    "SynthWave Labs", "Digital Forge", "Nexus Technologies", "Pulse Digital",
    "Vortex Systems", "Helix Data", "EchoTech", "Stratos Cloud",
    "NovaSoft", "TerraByte Inc", "LogicFlow", "SparkNet", "CoreStack",
    "Vertex AI Labs", "DeepMind Solutions", "NeuralPath Inc",
    "Fusion Analytics", "CyberShield Security", "GreenTech Solutions",
    "MedTech Innovations", "FinanceAI Corp", "EduTech Platform",
    "RetailSmart Inc", "AutoDrive Systems", "HealthData Analytics",
]

# ============================================================
# ARCHETYPE DEFINITIONS
# ============================================================

ARCHETYPES = {
    "strong": {
        "description": "Highly qualified, exceeds requirements",
        "education_level_weights": {"phd": 0.15, "master": 0.45, "bachelor": 0.40},
        "experience_years": (5, 15),
        "num_positions": (3, 6),
        "skill_count_range": (12, 20),
        "num_projects": (2, 4),
        "num_certifications": (2, 5),
        "language_count": (2, 4),
        "has_achievements": True,
        "has_leadership": True,
        "company_tier": "top",  # FAANG-like companies
        "summary_style": "executive",
    },
    "normal": {
        "description": "Moderately qualified, meets most requirements",
        "education_level_weights": {"bachelor": 0.50, "master": 0.30, "associate": 0.15, "high_school": 0.05},
        "experience_years": (1, 6),
        "num_positions": (2, 4),
        "skill_count_range": (6, 12),
        "num_projects": (1, 2),
        "num_certifications": (0, 2),
        "language_count": (1, 3),
        "has_achievements": False,
        "has_leadership": False,
        "company_tier": "mid",
        "summary_style": "standard",
    },
    "weak": {
        "description": "Underqualified, missing key requirements",
        "education_level_weights": {"high_school": 0.30, "associate": 0.35, "bachelor": 0.30, "master": 0.05},
        "experience_years": (0, 2),
        "num_positions": (0, 2),
        "skill_count_range": (2, 6),
        "num_projects": (0, 1),
        "num_certifications": (0, 1),
        "language_count": (1, 2),
        "has_achievements": False,
        "has_leadership": False,
        "company_tier": "low",
        "summary_style": "minimal",
    },
}


def weighted_choice(weights_dict):
    """Pick a key from a dict of {key: weight}."""
    items = list(weights_dict.items())
    keys = [k for k, v in items]
    weights = [v for k, v in items]
    return random.choices(keys, weights=weights, k=1)[0]


def generate_experience_description(title, domain, years, is_senior=False):
    """Generate realistic bullet points for a job position."""
    bullets = []
    num_bullets = random.randint(3, 6) if is_senior else random.randint(2, 4)

    templates = {
        "backend": [
            "Designed and implemented RESTful APIs serving {scale} using {tech}",
            "Reduced database query latency by {percent}% through optimization of {db} queries",
            "Led migration from {old_tech} to {new_tech}, improving system reliability by {percent}%",
            "Built automated CI/CD pipelines using {tool} reducing deployment time by {percent}%",
            "Collaborated with cross-functional teams to deliver {feature} on schedule",
            "Mentored {num} junior developers through code reviews and pair programming",
            "Implemented caching strategies with {tech} reducing API response time by {percent}%",
            "Designed microservices architecture handling {scale} daily requests",
            "Wrote comprehensive unit and integration tests achieving {percent}% code coverage",
            "Participated in on-call rotation, resolving {num} production incidents monthly",
        ],
        "data_science": [
            "Developed {model_type} models achieving {metric} of {score} on {task}",
            "Processed and analyzed datasets of {scale} records using {tool}",
            "Built ETL pipelines processing {scale} records daily with {tool}",
            "Created dashboards and reports for stakeholders using {tool}",
            "Collaborated with engineering teams to deploy models to production",
            "Conducted A/B testing resulting in {percent}% improvement in {metric}",
            "Performed feature engineering reducing model error by {percent}%",
            "Presented research findings to executive leadership team",
            "Mentored {num} junior analysts in statistical methods and ML techniques",
            "Published {num} papers in peer-reviewed conferences",
        ],
        "frontend": [
            "Developed responsive web applications using {framework} serving {scale} users",
            "Improved page load performance by {percent}% through code splitting and lazy loading",
            "Implemented component library with {num} reusable components",
            "Led redesign of {feature} resulting in {percent}% increase in user engagement",
            "Built accessible UI compliant with WCAG {level} standards",
            "Integrated {num} third-party APIs and services",
            "Mentored {num} junior developers on React best practices",
            "Implemented real-time features using WebSockets serving {scale} concurrent users",
            "Reduced bundle size by {percent}% through tree-shaking and optimization",
            "Collaborated with designers to implement pixel-perfect UI from Figma mockups",
        ],
    }

    domain_templates = templates.get(domain, templates["backend"])

    for _ in range(num_bullets):
        template = random.choice(domain_templates)
        bullet = template.format(
            scale=random.choice(["10K+", "100K+", "1M+", "50K+", "500K+", "10K daily"]),
            tech=random.choice(["Python", "Node.js", "Go", "Java", "TypeScript"]),
            db=random.choice(["PostgreSQL", "MySQL", "MongoDB", "Redis"]),
            old_tech=random.choice(["monolith", "legacy REST API", "SOAP service", "manual deployment"]),
            new_tech=random.choice(["microservices", "GraphQL", "gRPC", "Kubernetes"]),
            tool=random.choice(["Docker", "Kubernetes", "Jenkins", "GitHub Actions", "Terraform"]),
            feature=random.choice(["payment system", "user dashboard", "real-time analytics", "recommendation engine"]),
            num=random.randint(2, 8),
            percent=random.randint(15, 60),
            model_type=random.choice(["classification", "regression", "NLP", "deep learning", "ensemble"]),
            metric=random.choice(["accuracy", "F1 score", "precision", "recall", "AUC-ROC"]),
            score=f"{random.uniform(0.85, 0.99):.2f}",
            task=random.choice(["customer churn prediction", "fraud detection", "sentiment analysis", "recommendation"]),
            level=random.choice(["2.1", "AA", "A"]),
            framework=random.choice(["React", "Vue.js", "Angular", "Next.js", "Svelte"]),
        )
        bullets.append(bullet)

    return bullets


def generate_profile(archetype_name, domain, profile_id):
    """Generate a single candidate profile based on archetype and domain."""
    archetype = ARCHETYPES[archetype_name]

    # --- Personal Info ---
    gender = random.choice(["M", "F"])
    if gender == "M":
        first_name = fake.first_name_male()
    else:
        first_name = fake.first_name_female()
    last_name = fake.last_name()

    # --- Education ---
    edu_level = weighted_choice(archetype["education_level_weights"])
    edu_info = EDUCATION_LEVELS[edu_level]
    field = random.choice(edu_info["field_options"]) if edu_info["field_options"] else ""
    university = random.choice(UNIVERSITIES)
    gpa = None
    if archetype_name == "strong":
        gpa = round(random.uniform(3.5, 4.0), 2)
    elif archetype_name == "normal":
        gpa = round(random.uniform(2.8, 3.7), 2)
    elif archetype_name == "weak":
        gpa = round(random.uniform(2.0, 3.2), 2)

    # Education dates
    edu_end_year = random.randint(2015, 2024)
    edu_duration = {"high_school": 4, "associate": 2, "bachelor": 4, "master": 2, "phd": 5}
    edu_start_year = edu_end_year - edu_duration.get(edu_level, 4)

    education = [{
        "degree": edu_info["degree"],
        "field": field,
        "school": university,
        "start_date": f"{edu_start_year}",
        "end_date": f"{edu_end_year}",
        "details": f"GPA: {gpa}" if gpa else "",
    }]

    # Add second education for strong candidates
    if archetype_name == "strong" and random.random() > 0.4:
        second_edu = weighted_choice({"master": 0.6, "bachelor": 0.4})
        second_info = EDUCATION_LEVELS[second_edu]
        second_field = random.choice(second_info["field_options"]) if second_info["field_options"] else ""
        second_end = edu_end_year - random.randint(2, 4)
        second_start = second_end - edu_duration.get(second_edu, 2)
        education.insert(0, {
            "degree": second_info["degree"],
            "field": second_field,
            "school": random.choice(UNIVERSITIES),
            "start_date": f"{second_start}",
            "end_date": f"{second_end}",
            "details": f"GPA: {round(random.uniform(3.6, 4.0), 2)}",
        })

    # --- Experience ---
    exp_years = random.randint(*archetype["experience_years"])
    num_positions = random.randint(*archetype["num_positions"])
    experience = []

    templates = EXPERIENCE_TEMPLATES.get(domain, EXPERIENCE_TEMPLATES["backend"])

    for i in range(num_positions):
        template = random.choice(templates)
        position_years = max(1, exp_years // num_positions + random.randint(-1, 1))
        start_year = 2024 - exp_years + sum(max(1, exp_years // num_positions) for _ in range(i))
        end_year = start_year + position_years

        is_senior = "Senior" in template["title"] or "Lead" in template["title"] or "Staff" in template["title"]

        company = random.choice(COMPANIES)
        if archetype_name == "strong" and random.random() > 0.5:
            # Strong candidates more likely to have big-company experience
            company = random.choice(["Google", "Amazon", "Microsoft", "Meta", "Apple", "Netflix", "Stripe", "Airbnb", "Uber", "Spotify"])

        location = fake.city() + ", " + fake.state_abbr()

        description = generate_experience_description(
            template["title"], domain, position_years, is_senior
        )

        experience.append({
            "title": template["title"],
            "company": company,
            "location": location,
            "start_date": f"{start_year}",
            "end_date": f"{end_year}" if end_year <= 2024 else "Present",
            "description": description,
        })

    # Sort experience by start date (most recent first)
    experience.sort(key=lambda x: x["start_date"], reverse=True)

    # --- Skills ---
    skill_pool = SKILL_POOLS.get(domain, SKILL_POOLS["backend"])
    num_skills = random.randint(*archetype["skill_count_range"])

    selected_skills = {}
    all_skills = []
    for category, skills_list in skill_pool.items():
        for skill in skills_list:
            all_skills.append((category, skill))

    random.shuffle(all_skills)
    for category, skill in all_skills[:num_skills]:
        if category not in selected_skills:
            selected_skills[category] = []
        selected_skills[category].append(skill)

    # --- Projects ---
    projects = []
    for _ in range(random.randint(*archetype["num_projects"])):
        project_names = [
            "Real-time Chat Application", "E-commerce Platform", "Personal Portfolio Website",
            "Data Pipeline Framework", "Machine Learning Model Registry", "CI/CD Automation Tool",
            "REST API Gateway", "Distributed Cache System", "Natural Language Processing Toolkit",
            "Recommendation Engine", "Image Classification System", "Task Management Dashboard",
            "Weather Prediction Model", "Sentiment Analysis API", "Code Review Bot",
        ]
        projects.append({
            "name": random.choice(project_names),
            "description": f"Built using {random.choice(list(skill_pool.get('frameworks', ['Python'])))}. "
                          f"{'Deployed on ' + random.choice(['AWS', 'GCP', 'Heroku', 'Vercel']) + '. ' if random.random() > 0.5 else ''}"
                          f"{'Open source with ' + str(random.randint(10, 500)) + ' stars. ' if random.random() > 0.7 else ''}"
                          f"{'Used by ' + str(random.randint(100, 10000)) + ' users.' if random.random() > 0.6 else ''}",
        })

    # --- Certifications ---
    cert_pool = [
        {"name": "AWS Certified Solutions Architect", "issuer": "Amazon Web Services"},
        {"name": "AWS Certified Developer – Associate", "issuer": "Amazon Web Services"},
        {"name": "Google Cloud Professional Cloud Architect", "issuer": "Google Cloud"},
        {"name": "Microsoft Certified: Azure Developer Associate", "issuer": "Microsoft"},
        {"name": "Certified Kubernetes Administrator (CKA)", "issuer": "Cloud Native Computing Foundation"},
        {"name": "Docker Certified Associate", "issuer": "Docker Inc."},
        {"name": "TensorFlow Developer Certificate", "issuer": "Google"},
        {"name": "Certified Information Systems Security Professional (CISSP)", "issuer": "ISC²"},
        {"name": "HashiCorp Certified: Terraform Associate", "issuer": "HashiCorp"},
        {"name": "MongoDB Certified Developer Associate", "issuer": "MongoDB Inc."},
        {"name": "Certified ScrumMaster (CSM)", "issuer": "Scrum Alliance"},
        {"name": "PMP - Project Management Professional", "issuer": "PMI"},
    ]
    certifications = random.sample(cert_pool, random.randint(*archetype["num_certifications"]))

    # --- Languages ---
    language_pool = [
        {"name": "English", "levels": ["Native", "Fluent", "Professional"]},
        {"name": "French", "levels": ["Native", "Fluent", "Professional", "Intermediate"]},
        {"name": "Spanish", "levels": ["Native", "Fluent", "Professional", "Intermediate", "Basic"]},
        {"name": "German", "levels": ["Fluent", "Professional", "Intermediate", "Basic"]},
        {"name": "Mandarin", "levels": ["Native", "Fluent", "Professional", "Intermediate"]},
        {"name": "Arabic", "levels": ["Native", "Fluent", "Professional"]},
        {"name": "Portuguese", "levels": ["Native", "Fluent", "Professional", "Intermediate"]},
        {"name": "Japanese", "levels": ["Professional", "Intermediate", "Basic"]},
        {"name": "Hindi", "levels": ["Native", "Fluent"]},
        {"name": "Russian", "levels": ["Native", "Fluent", "Intermediate"]},
    ]

    num_langs = random.randint(*archetype["language_count"])
    languages = []
    # Always include English (or a native language)
    native_lang = random.choice(["English", "French", "Spanish", "Arabic", "Portuguese"])
    languages.append({"name": native_lang, "level": "Native"})

    remaining_langs = [l for l in language_pool if l["name"] != native_lang]
    for lang in random.sample(remaining_langs, min(num_langs - 1, len(remaining_langs))):
        languages.append({"name": lang["name"], "level": random.choice(lang["levels"])})

    # --- Summary ---
    domain_display = {"backend": "Backend Engineering", "data_science": "Data Science", "frontend": "Frontend Development"}
    years_text = f"{exp_years}+ years" if exp_years > 0 else "Entry-level"

    if archetype_name == "strong":
        summary_templates = [
            f"Results-driven {domain_display[domain]} professional with {years_text} of experience building scalable, high-performance systems. Proven track record of leading technical initiatives and delivering measurable business impact. Passionate about clean code, system design, and mentoring engineering teams.",
            f"Accomplished {domain_display[domain]} expert with {years_text} of hands-on experience across the full development lifecycle. Demonstrated ability to architect and implement complex systems serving millions of users. Strong background in technical leadership and cross-team collaboration.",
            f"Senior {domain_display[domain]} professional with {years_text} of progressive experience at top-tier technology companies. Expert in designing distributed systems and optimizing application performance. Published researcher and active contributor to open-source projects.",
        ]
    elif archetype_name == "normal":
        summary_templates = [
            f"Motivated {domain_display[domain]} professional with {years_text} of experience. Skilled in modern technologies and frameworks. Looking to leverage technical skills and problem-solving abilities in a challenging role.",
            f"Dedicated {domain_display[domain]} developer with {years_text} of practical experience. Strong foundation in computer science principles and hands-on experience with relevant technologies. Eager to contribute to a collaborative engineering team.",
            f"Detail-oriented {domain_display[domain]} practitioner with {years_text} of industry experience. Comfortable working in agile environments and collaborating with cross-functional teams. Committed to continuous learning and professional growth.",
        ]
    else:  # weak
        summary_templates = [
            f"Aspiring {domain_display[domain]} professional with basic knowledge of programming concepts. Motivated to learn and grow in a technical role. Quick learner with strong work ethic.",
            f"Entry-level candidate interested in {domain_display[domain]}. Completed coursework in fundamentals and eager to apply theoretical knowledge in a practical setting. Strong communication skills.",
            f"Recent graduate with foundational knowledge in {domain_display[domain]}. Self-taught in several technologies through online courses and personal projects. Seeking an opportunity to begin a career in technology.",
        ]

    summary = random.choice(summary_templates)

    # --- Contact Info ---
    email = f"{first_name.lower()}.{last_name.lower()}@{fake.free_email_domain()}"
    phone = fake.phone_number()
    location = fake.city() + ", " + fake.state_abbr()
    linkedin = f"linkedin.com/in/{first_name.lower()}-{last_name.lower()}-{random.randint(100, 999)}"

    # --- Title ---
    title_map = {
        "backend": random.choice(["Backend Developer", "Software Engineer", "Backend Engineer", "Full Stack Developer"]),
        "data_science": random.choice(["Data Scientist", "ML Engineer", "Data Analyst", "Research Scientist"]),
        "frontend": random.choice(["Frontend Developer", "UI/UX Developer", "Web Developer", "Software Engineer"]),
    }

    return {
        "id": f"profile_{profile_id:04d}",
        "archetype": archetype_name,
        "domain": domain,
        "first_name": first_name,
        "last_name": last_name,
        "title": title_map[domain],
        "email": email,
        "phone": phone,
        "location": location,
        "linkedin": linkedin,
        "summary": summary,
        "skills": selected_skills,
        "experience": experience,
        "education": education,
        "certifications": certifications,
        "languages": languages,
        "projects": projects,
        "gpa": gpa,
        "total_experience_years": exp_years,
        "education_level": edu_level,
    }


def generate_all_profiles(counts, output_path):
    """Generate profiles for all archetypes and domains."""
    profiles = []
    profile_id = 0
    domains = ["backend", "data_science", "frontend"]

    for archetype_name in ["strong", "normal", "weak", "random"]:
        if archetype_name == "random":
            count = counts.get("random", 0)
            for _ in range(count):
                domain = random.choice(domains)
                # Random archetype: pick from any archetype randomly
                actual_archetype = random.choice(["strong", "normal", "weak"])
                profile = generate_profile(actual_archetype, domain, profile_id)
                profile["archetype"] = "random"
                profiles.append(profile)
                profile_id += 1
        else:
            count = counts.get(archetype_name, 0)
            for _ in range(count):
                domain = random.choice(domains)
                profile = generate_profile(archetype_name, domain, profile_id)
                profiles.append(profile)
                profile_id += 1

    # Save profiles
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)

    # Print summary
    print(f"\n{'='*60}")
    print(f"  Generated {len(profiles)} profiles")
    print(f"{'='*60}")

    for archetype in ["strong", "normal", "weak", "random"]:
        subset = [p for p in profiles if p["archetype"] == archetype]
        if subset:
            avg_exp = sum(p["total_experience_years"] for p in subset) / len(subset)
            edu_dist = {}
            for p in subset:
                edu_dist[p["education_level"]] = edu_dist.get(p["education_level"], 0) + 1
            print(f"\n  {archetype.upper()} ({len(subset)} profiles):")
            print(f"    Avg experience: {avg_exp:.1f} years")
            print(f"    Education: {edu_dist}")

    print(f"\n  Output: {output}")
    return profiles


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic CV profiles")
    parser.add_argument("--strong", type=int, default=5, help="Number of strong profiles")
    parser.add_argument("--normal", type=int, default=10, help="Number of normal profiles")
    parser.add_argument("--weak", type=int, default=5, help="Number of weak profiles")
    parser.add_argument("--random", type=int, default=50, help="Number of random profiles")
    parser.add_argument("--output", type=str, default="data/synthetic/profiles.json", help="Output file path")
    args = parser.parse_args()

    counts = {
        "strong": args.strong,
        "normal": args.normal,
        "weak": args.weak,
        "random": args.random,
    }

    generate_all_profiles(counts, args.output)
