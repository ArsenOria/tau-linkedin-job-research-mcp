"""Synthetic examples, deliberately not claims about real vacancies."""
from .models import Job, now_iso


def demo_jobs() -> list[Job]:
    examples = [
        ("9999900001", "Product Analyst", "Example Orchard", "Berlin, Germany", "remote",
         "SYNTHETIC DEMO, NOT A LIVE VACANCY. SQL, Python and product experimentation. Sponsorship not stated.", True),
        ("9999900002", "Senior Data Analyst", "Example Harbor", "London, United Kingdom", "hybrid",
         "SYNTHETIC DEMO, NOT A LIVE VACANCY. SQL, Tableau and stakeholder reporting.", False),
        ("9999900003", "Product Analytics Engineer", "Example Birch", "European locations unspecified", "remote",
         "SYNTHETIC DEMO, NOT A LIVE VACANCY. SQL, dbt and Python. Remote residence restrictions unknown.", None),
    ]
    return [Job(title=title, external_id=job_id, company=company, location=location, workplace=workplace,
                description=description, easy_apply=easy, source="demo", observed_at=now_iso())
            for job_id, title, company, location, workplace, description, easy in examples]
