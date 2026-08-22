from app.agents.career import analyze_skill_gap, compare_roles, readiness_from_gaps
from app.agents.interview import apply_followup, as_score, build_report, heuristic_eval, merge_evaluation, plan_questions
from app.agents.resume import ats_score, extract_keywords, profile_to_resume_content
from app.services.billing import limits_for
from app.services.catalog import get_role, infer_level, normalize_role, roadmap_catalog_mismatch
from app.services.export import render_pdf
from app.services.facts import fact_check_resume
from app.services.parsers import parse_resume_text
from app.services.voice import analyze_speech
from types import SimpleNamespace


def test_python_skill_detected():
    assert infer_level("Python", ["Python", "FastAPI"]) != "missing"


def test_skill_gap_ranks_missing_high():
    gaps = analyze_skill_gap(["Python"], "AI Engineer")
    docker = next(g for g in gaps if "Docker" in g["skill"])
    assert docker["gap"] in ("high", "medium")
    assert 0 <= readiness_from_gaps(gaps) <= 100


def test_architecture_is_not_machine_learning():
    assert normalize_role("architecture") == "architect"
    role = get_role("architecture")
    skills = {s.lower() for s in role["required"]}
    assert "python" not in skills
    assert "machine learning" not in skills
    assert any("cad" in s or "design" in s or "drawing" in s for s in skills)


def test_fine_arts_is_not_ai_engineer():
    artist = get_role("fine arts")
    ai = get_role("AI Engineer")
    assert set(artist["required"]) != set(ai["required"])
    assert "Python" not in artist["required"]
    assert "Machine Learning" not in artist["required"]


def test_intern_does_not_alias_to_ai_engineer():
    assert normalize_role("intern") == "intern"
    assert normalize_role("intern") != "ai engineer"


def test_stale_ml_roadmap_for_architect():
    fake_gap = [{"skill": "Machine Learning"}, {"skill": "Python"}, {"skill": "Docker"}]
    assert roadmap_catalog_mismatch("architecture", fake_gap)
    real = [{"skill": s} for s in get_role("architect")["required"]]
    assert not roadmap_catalog_mismatch("architecture", real)


def test_equal_fit_does_not_declare_a_winner():
    result = compare_roles([], "AI Engineer", "artist")
    assert result["role_a"]["readiness"] == result["role_b"]["readiness"]
    assert result["closer"] is None
    assert "neither" in result["recommendation"].lower()


def test_empty_resume_ats_is_not_inflated():
    result = ats_score(
        {
            "contact": {"name": "A", "email": "a@b.com"},
            "summary": "nothing",
            "skills": {"programming": []},
            "experience": [],
            "education": [],
            "projects": [],
        },
        "",
    )
    assert result["had_jd"] is False
    assert result["ats_readiness"] < 25


def test_placeholder_summary_not_copied_to_resume():
    content = profile_to_resume_content("Rimsha", "r@example.com", {"summary": "nothing", "skills": {}, "experience": [], "education": [], "projects": [], "career_goals": {}})
    assert "nothing" not in (content["summary"] or "").lower()


def test_interview_questions_change_each_session(monkeypatch):
    from app.agents import interview as interview_mod

    monkeypatch.setattr(interview_mod, "gateway", SimpleNamespace(enabled=False))
    first = [q["prompt"] for q in plan_questions("Artist", "behavioral", 6, "student artist", "")]
    second = [q["prompt"] for q in plan_questions("Artist", "behavioral", 6, "student artist", "", avoid_prompts=first)]
    assert first
    assert not set(first) & set(second)
    openers = {plan_questions("Software Engineer", "mixed", 6, "", "")[0]["prompt"] for _ in range(8)}
    assert len(openers) > 1


def test_followup_does_not_grow_interview():
    qs = [
        {"index": i, "prompt": f"Q{i}", "is_followup": False, "answer": None, "session_total": 6, "type": "craft"}
        for i in range(6)
    ]
    grown = apply_followup(qs, 0, {"needs_followup": True, "followup_question": "Say more about the brief."})
    assert len(grown) == 6
    assert grown[1]["is_followup"] is True
    assert grown[1]["prompt"] == "Say more about the brief."


def test_ats_does_not_invent_keywords_as_skills():
    content = {
        "contact": {"name": "A", "email": "a@b.com"},
        "summary": "Python developer",
        "skills": {"programming": ["Python"], "technical": []},
        "experience": [],
        "education": [],
        "projects": [],
    }
    result = ats_score(content, "Looking for Kubernetes and Python engineers")
    assert "Python" in result["matched_keywords"] or any("python" in k.lower() for k in result["matched_keywords"])
    assert result["missing_keywords"]
    assert any("estimate" in n.lower() for n in result["notes"])


def test_parse_resume_extracts_email():
    text = "Rimsha Ali\nrimsha@example.com\n\nSkills\nPython, SQL\n"
    parsed = parse_resume_text(text)
    assert parsed["contact"]["email"] == "rimsha@example.com"


def test_keyword_extract_filters_boilerplate():
    kws = extract_keywords("We are looking for a Python engineer with Docker and strong ability to work")
    assert "Python" in kws
    assert "ability" not in [k.lower() for k in kws]


def test_fact_check_drops_invented_employer():
    content = {
        "experience": [{"company": "FakeCorp AI", "title": "Intern", "technologies": ["Python", "Kubernetes"]}],
        "projects": [{"name": "Secret Moon Base"}],
        "education": [],
        "skills": {"programming": ["Python", "COBOL"]},
        "flagged_missing": [],
    }
    allowed = {
        "companies": ["Campus AI Club"],
        "titles": ["Project Lead", "Intern"],
        "projects": ["AI Career Coach"],
        "skills": ["Python"],
        "schools": [],
        "degrees": [],
    }
    cleaned = fact_check_resume(content, allowed)
    assert cleaned["experience"] == []
    assert cleaned["projects"] == []
    assert "Python" in cleaned["skills"]["programming"]
    assert "COBOL" not in cleaned["skills"]["programming"]
    assert cleaned["flagged_missing"]


def test_voice_analytics_counts_fillers_and_pace():
    metrics = analyze_speech("Um I uh delivered the brief like on time.", duration_ms=4000)
    assert metrics["filler_count"] >= 2
    assert metrics["word_count"] > 0
    assert metrics["words_per_minute"] > 0
    assert "pace" in metrics["speaking_pace"] or metrics["speaking_pace"] in ("fast", "slow", "steady")


def test_premium_unlocks_voice_and_extra_templates():
    premium = limits_for(SimpleNamespace(plan="Premium"))
    assert premium["voice_interviews"] is True
    assert "compact" in premium["templates"]
    pro = limits_for(SimpleNamespace(plan="pro"))
    assert pro["voice_interviews"] is False
    assert "compact" not in pro["templates"]


def test_pdf_export_handles_long_project_tech():
    data = render_pdf(
        {
            "contact": {"name": "Test User", "email": "a@b.com", "links": "https://example.com/very-long-portfolio-path"},
            "summary": "Builder of tools.",
            "skills": {"programming": ["Python", "SQL"]},
            "experience": [{"title": "Intern", "company": "Studio", "responsibilities": ["Shipped a demo"]}],
            "projects": [
                {
                    "name": "Portfolio site",
                    "description": "Personal work",
                    "technologies": ["https://github.com/example/this-is-a-very-long-unbroken-url-path-that-used-to-crash-fpdf"] * 4,
                }
            ],
            "education": [{"degree": "BFA", "institution": "Art School"}],
        },
        "portfolio",
    )
    assert data.startswith(b"%PDF")


def test_interview_report_accepts_word_scores():
    assert as_score("Fair") == 62
    report = build_report(
        [
            {
                "type": "behavioral",
                "answer": "I led a project.",
                "evaluation": {"overall": "Fair", "scores": {"clarity": "good", "structure": "weak", "relevance": 70}},
            }
        ],
        "Architect",
    )
    assert report["overall"] == 62
    assert report["communication"] > 0


def test_github_handle_from_url():
    from app.services.social import github_handle

    assert github_handle("https://github.com/octocat") == "octocat"
    assert github_handle("@rimsha") == "rimsha"


def test_pdf_does_not_print_internal_flags():
    data = render_pdf(
        {
            "contact": {"name": "Ada Lovelace", "email": "ada@example.com", "location": "London"},
            "summary": "Mathematician and writer.",
            "skills": {"technical": ["Analysis"]},
            "experience": [{"title": "Analyst", "company": "Analytical Engine", "start_date": "1842", "end_date": "1843", "responsibilities": ["Documented the engine."]}],
            "education": [{"degree": "Private study", "institution": "London"}],
            "projects": [],
            "flagged_missing": ["Do not print this employer note"],
        },
        "executive",
    )
    assert data.startswith(b"%PDF")
    # Helvetica latin-1 encoding still contains the summary, not the internal note.
    assert b"Do not print this employer note" not in data


def test_mcp_tools_are_named():
    from app.api.mcp import TOOLS

    names = {t["name"] for t in TOOLS}
    assert {"get_dashboard", "analyze_skill_gap", "career_analytics", "list_reminders"} <= names


def test_short_voice_answer_is_not_stuck_at_sixty():
    weak = heuristic_eval("behavioral", "I don't know.")
    assert weak["overall"] < 40
    stuck = {"overall": 60, "scores": {"overall": 60, "clarity": 60}, "strengths": ["ok"], "weaknesses": []}
    merged = merge_evaluation(stuck, weak, "I don't know.")
    assert merged["overall"] < 45
    strong_text = (
        "In my last studio review I owned the site plan for a 12-unit housing block. "
        "The brief was a tight budget and a flood-risk site. I mapped drainage, cut the footprint 8 percent, "
        "and presented three options to the client. They chose the mid option and we submitted on time."
    )
    strong = heuristic_eval("behavioral", strong_text)
    assert strong["overall"] > 60
    merged_strong = merge_evaluation({"overall": 60, "scores": {"overall": 60}}, strong, strong_text)
    assert merged_strong["overall"] > 65


def test_coursework_and_extra_skills_show_on_gap():
    from app.agents.career import analyze_skill_gap
    from app.services.catalog import collect_profile_skills

    owned = collect_profile_skills(
        {
            "skills": {"programming": ["Python"], "frameworks": ["LangChain"]},
            "education": [{"coursework": ["Machine Learning", "NLP"], "major": "Artificial Intelligence"}],
            "experience": [{"technologies": ["FastAPI"]}],
            "projects": [{"technologies": ["Next.js"]}],
        }
    )
    assert "Machine Learning" in owned
    assert "NLP" in owned
    gaps = analyze_skill_gap(owned, "AI Engineer")
    names = {g["skill"] for g in gaps}
    assert "NLP" in names or any("nlp" in s.lower() for s in names)
    ml = next(g for g in gaps if "Machine Learning" in g["skill"])
    assert ml["current"] != "Missing"


def test_roadmap_is_weekday_plan():
    from app.agents.career import analyze_skill_gap, build_roadmap

    gaps = analyze_skill_gap(["Python", "SQL", "LangChain"], "AI Engineer")
    plan = build_roadmap(gaps, 1, "AI Engineer")
    assert len(plan) == 4
    assert all(len(w["tasks"]) == 5 for w in plan)
    assert plan[0]["tasks"][0]["day"] == "Monday"
    titles = " ".join(t["title"] for w in plan for t in w["tasks"])
    assert "Learn" in titles and "Practice" in titles


def test_skill_roadmap_stays_on_that_skill():
    from app.agents.career import build_roadmap

    plan = build_roadmap(
        [{"skill": "Supabase", "target": "Your addition", "gap": "low"}],
        duration_months=1,
        target_role="AI Engineer",
        focus_skill="research writing",
        duration_unit="weeks",
        duration_value=2,
    )
    assert len(plan) == 2
    blob = " ".join(t["title"] + t["skill"] for w in plan for t in w["tasks"]).lower()
    assert "supabase" not in blob
    assert "research" in blob or "source" in blob or "draft" in blob


def test_custom_duration_days():
    from app.agents.career import build_roadmap

    plan = build_roadmap([], focus_skill="piano", duration_unit="days", duration_value=8)
    assert len(plan) == 2
    assert len(plan[0]["tasks"]) == 5
    assert len(plan[1]["tasks"]) == 3


def test_listed_skills_are_on_track_not_a_low_rating():
    from app.agents.career import analyze_skill_gap, fit_breakdown, readiness_from_gaps

    gaps = analyze_skill_gap(["Python", "SQL", "LangChain", "FastAPI", "Git", "Docker"], "AI Engineer")
    sql = next(g for g in gaps if g["skill"] == "SQL")
    lc = next(g for g in gaps if "LangChain" in g["skill"])
    assert sql["priority_label"] == "On track"
    assert lc["priority_label"] == "On track"
    assert "low remaining" in sql["why_it_matters"].lower() or "on track" in sql["why_it_matters"].lower()
    br = fit_breakdown(gaps, readiness_from_gaps(gaps))
    assert "SQL" in br["on_track"]
    assert br["percent"] > 0


def test_valid_card_is_accepted_and_pan_is_not_returned():
    from datetime import date

    from app.services.cards import luhn_ok, validate_card

    assert luhn_ok("4242424242424242")
    assert not luhn_ok("4242424242424243")
    year = date.today().year + 3
    info = validate_card("Ada Lovelace", "4242 4242 4242 4242", 12, year, "123")
    assert info.last4 == "4242"
    assert info.brand == "visa"


def test_free_plan_replaces_resume_at_cap_paid_plans_block():
    from app.api.resume import _can_replace_at_cap
    from app.services.billing import PLAN_LIMITS

    assert _can_replace_at_cap(PLAN_LIMITS["free"], 1)
    assert not _can_replace_at_cap(PLAN_LIMITS["pro"], 8)
    assert not _can_replace_at_cap(PLAN_LIMITS["premium"], 1)


def test_subscription_events_map_to_local_plans():
    from app.services.checkout import plan_from_price_id, plan_from_subscription

    assert plan_from_subscription({"status": "canceled"}) == "free"
    assert plan_from_subscription({"status": "unpaid"}) == "free"
    assert plan_from_subscription({"status": "incomplete_expired"}) == "free"
    assert plan_from_subscription({"status": "past_due", "items": {"data": []}}) is None
    unknown_active = {
        "status": "active",
        "items": {"data": [{"price": {"id": "price_unknown"}}]},
    }
    assert plan_from_subscription(unknown_active) is None
    assert plan_from_price_id("") is None


def test_invalid_or_expired_card_is_rejected():
    from datetime import date

    from fastapi import HTTPException

    from app.services.cards import validate_card

    year = date.today().year + 3
    try:
        validate_card("Ada Lovelace", "0000000000000000", 12, year, "123")
        raise AssertionError("all-zero card should fail")
    except HTTPException:
        pass
    try:
        validate_card("Ada Lovelace", "4242424242424242", 1, 2020, "123")
        raise AssertionError("expired card should fail")
    except HTTPException:
        pass
    try:
        validate_card("Ada Lovelace", "4242424242424242", 12, year, "12")
        raise AssertionError("short CVC should fail")
    except HTTPException:
        pass

