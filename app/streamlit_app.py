"""Streamlit interface (English, Hindi, Kannada) for evidence-grounded AgriGuide AI.

Only presentation lives here. Questions go to the existing pipeline through
``submit_question`` (English) and ``submit_multilingual_question`` (Hindi,
Kannada); answers, citations and abstentions are shown exactly as the pipeline
returns them. All dynamic text is HTML-escaped before it is placed in markup.
"""

from __future__ import annotations

import base64
import functools
import html
import logging
import sys
from pathlib import Path

import streamlit as st

# `streamlit run app/streamlit_app.py` puts app/ (not the project root) on the
# import path, so `app` and `src` would not be importable without this.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bootstrap import ApplicationBootstrapError, build_pipeline  # noqa: E402
from src.multilingual_flow import LANGUAGE_NAMES, MultilingualResult, answer_multilingual  # noqa: E402
from src.rag_pipeline import AnswerResult, PROCESSING_ERROR_MESSAGE  # noqa: E402
from src.translation_client import SubprocessTranslator  # noqa: E402

LANGUAGE_OPTIONS = {
    "English": "en",
    "हिन्दी": "hi",
    "ಕನ್ನಡ": "kn",
}

# Example questions per language. The Hindi and Kannada wording is copied
# verbatim from manually approved questions in evaluation/test_cases.jsonl
# (drone_01, fert_01_alt, crop_02, hort_01) so no unreviewed translation is
# shown. Tapping one runs the real pipeline; no answer is stored here.
SUGGESTED_QUESTIONS = {
    "en": (
        ("Drone spraying", "Should pesticide be sprayed with a drone if heavy rain is forecast in the next one to two days?"),
        ("Fertilizer", "What gypsum rate per hectare is recommended for groundnut?"),
        ("Sowing", "What seed rate and row spacing are recommended for line sowing of finger millet?"),
        ("Vegetables", "What planting spacing is recommended for tomato varieties PKM 1, Paiyur 1 and COTH 2?"),
    ),
    "hi": (
        ("Drone spraying", "यदि अगले एक-दो दिनों में भारी बारिश का पूर्वानुमान हो, तो क्या ड्रोन से कीटनाशक का छिड़काव करना चाहिए?"),
        ("Fertilizer", "मूंगफली के लिए प्रति हेक्टेयर जिप्सम की कितनी मात्रा अनुशंसित है?"),
        ("Sowing", "रागी की पंक्तिबद्ध बुवाई के लिए बीज दर और पंक्तियों के बीच की दूरी कितनी अनुशंसित है?"),
        ("Vegetables", "टमाटर की किस्मों PKM 1, Paiyur 1 और COTH 2 के लिए रोपण की दूरी कितनी अनुशंसित है?"),
    ),
    "kn": (
        ("Drone spraying", "ಮುಂದಿನ ಒಂದು-ಎರಡು ದಿನಗಳಲ್ಲಿ ಭಾರಿ ಮಳೆಯ ಮುನ್ಸೂಚನೆ ಇದ್ದರೆ ಡ್ರೋನ್‌ನಿಂದ ಕೀಟನಾಶಕ ಸಿಂಪಡಿಸಬಹುದೇ?"),
        ("Fertilizer", "ಕಡಲೆಕಾಯಿಗೆ ಪ್ರತಿ ಹೆಕ್ಟೇರ್‌ಗೆ ಎಷ್ಟು ಜಿಪ್ಸಮ್ ಶಿಫಾರಸು ಮಾಡಲಾಗಿದೆ?"),
        ("Sowing", "ರಾಗಿಯ ಸಾಲು ಬಿತ್ತನೆಗೆ ಶಿಫಾರಸು ಮಾಡಿದ ಬೀಜದ ದರ ಮತ್ತು ಸಾಲುಗಳ ನಡುವಿನ ಅಂತರ ಎಷ್ಟು?"),
        ("Vegetables", "ಟೊಮೆಟೊ ತಳಿಗಳಾದ PKM 1, Paiyur 1 ಮತ್ತು COTH 2 ಗೆ ಶಿಫಾರಸು ಮಾಡಿದ ನಾಟಿ ಅಂತರ ಎಷ್ಟು?"),
    ),
}
MAX_HISTORY = 20
ABSTENTION_TIP = (
    "Tip: name the crop and what you want to know, for example the seed rate, "
    "spacing, irrigation stage or fertilizer dose."
)

LOGGER = logging.getLogger(__name__)


@st.cache_resource(show_spinner=False)
def _load_pipeline():
    return build_pipeline()


@st.cache_resource(show_spinner=False)
def _load_translator():
    # Starts no process and loads no model until a Hindi/Kannada question needs one.
    return SubprocessTranslator()


def submit_question(pipeline, question: str) -> AnswerResult:
    """Run the existing RAG pipeline and turn unexpected errors into a safe result."""
    try:
        return pipeline.answer(question)
    except Exception as exc:
        LOGGER.error("Question submission failed (%s)", type(exc).__name__)
        return AnswerResult(
            question=question.strip(),
            mode="error",
            answer_kind="error",
            answer_text=PROCESSING_ERROR_MESSAGE,
            warnings=("question processing failed ({})".format(type(exc).__name__),),
        )


def submit_multilingual_question(pipeline, translator, question: str, language: str) -> MultilingualResult:
    """Answer in the selected language; English never touches the translator."""
    return answer_multilingual(
        lambda english_question: submit_question(pipeline, english_question),
        translator,
        question,
        language,
    )


# --------------------------------------------------------------------------
# Rendering. Each function takes ``ui`` (``st`` or a container) so it can be
# tested without a browser.
# --------------------------------------------------------------------------


def _esc(text) -> str:
    """Escape text for inline HTML; keep line breaks and stop "$" turning into math."""
    escaped = html.escape(str(text or ""), quote=False).replace("$", "&#36;")
    return "<br>".join(line.strip() for line in escaped.splitlines()) or ""


def _attr(text) -> str:
    return html.escape(str(text or ""), quote=True)


def _answer_card(ui, text: str, tone: str, language: str = "en", label: str | None = None) -> None:
    heading = '<div class="ag-answer-label">{}</div>'.format(_esc(label)) if label else ""
    ui.markdown(
        '<div class="ag-answer ag-answer--{}" lang="{}">{}<div class="ag-answer-text">{}</div></div>'.format(
            tone, _attr(language), heading, _esc(text)
        ),
        unsafe_allow_html=True,
    )


def _render_sources(ui, result: AnswerResult, translated: bool) -> None:
    if not result.sources:
        return
    count = len(result.sources)
    ui.markdown(
        '<div class="ag-sources-head"><span class="ag-sources-title">Sources</span>'
        '<span class="ag-sources-count">{} cited {}</span></div>'.format(
            count, "passage" if count == 1 else "passages"
        ),
        unsafe_allow_html=True,
    )
    if translated:
        ui.caption(
            "The source documents are written in English. Titles, page numbers and "
            "excerpts below are the original English text and are not translated."
        )
    for number, citation in enumerate(result.sources, start=1):
        organization = (
            '<div class="ag-source-org">{}</div>'.format(_esc(citation.organization))
            if citation.organization
            else ""
        )
        link = (
            '<a class="ag-source-link" href="{}#page={}" target="_blank" rel="noopener noreferrer">'
            "Open document at page {} &#8599;</a>".format(
                _attr(citation.url), int(citation.page_number), int(citation.page_number)
            )
            if citation.url
            else ""
        )
        ui.markdown(
            '<div class="ag-source">'
            '<div class="ag-source-head">'
            '<span class="ag-source-num">{num}</span>'
            '<div class="ag-source-meta"><div class="ag-source-title">Source {num}: {title}</div>{org}</div>'
            '<span class="ag-page" title="Page number in the PDF document">Page {page}</span>'
            "</div>"
            '<details class="ag-excerpt"><summary>Show the quoted source passage</summary>'
            '<div class="ag-excerpt-text" lang="en">{excerpt}</div></details>'
            "{link}"
            "</div>".format(
                num=number,
                title=_esc(citation.title),
                org=organization,
                page=int(citation.page_number),
                excerpt=_esc(citation.excerpt),
                link=link,
            ),
            unsafe_allow_html=True,
        )


def render_result(ui, result: AnswerResult) -> None:
    """Render an English answer with an explicit type and its source provenance."""
    if result.answer_kind == "extractive_evidence" and result.mode == "answered":
        ui.success("Extracted evidence")
        ui.caption("Quoted from retrieved source text; this is not an LLM-generated answer.")
        _answer_card(ui, result.answer_text, "evidence", label="From the source documents")
    elif result.answer_kind == "abstention" or result.mode == "abstained":
        ui.warning("Insufficient evidence")
        if result.warnings:
            ui.caption("Reason: {}".format(result.warnings[0]))
        _answer_card(ui, result.answer_text, "abstain")
        ui.markdown('<div class="ag-tip">{}</div>'.format(_esc(ABSTENTION_TIP)), unsafe_allow_html=True)
    else:
        ui.error("Error")
        _answer_card(ui, result.answer_text, "error")

    _render_sources(ui, result, translated=False)


def render_multilingual_result(ui, result: MultilingualResult) -> None:
    """Render a Hindi/Kannada response, separating the translation from the English evidence."""
    name = LANGUAGE_NAMES[result.language]
    english = result.english_result

    if result.status == "translated" and english is not None:
        answered = english.mode == "answered"
        if answered:
            ui.success("Extracted evidence (machine-translated to {})".format(name))
        else:
            ui.warning("Insufficient evidence")
            if english.warnings:
                ui.caption("Reason (from the English search): {}".format(english.warnings[0]))
        ui.caption(
            "Automatic {} translation (IndicTrans2) of the English evidence below; it may "
            "contain errors. Check the original English excerpts.".format(name)
        )
        _answer_card(
            ui,
            result.translated_answer,
            "evidence" if answered else "abstain",
            language=result.language,
            label="{} translation".format(name),
        )
        if result.english_question:
            ui.caption("Your question was understood as: {}".format(result.english_question))
        if not answered:
            ui.markdown('<div class="ag-tip">{}</div>'.format(_esc(ABSTENTION_TIP)), unsafe_allow_html=True)
        _answer_card(ui, english.answer_text, "english", label="Original English evidence")
        _render_sources(ui, english, translated=True)
        return

    if result.status == "translation_failed":
        ui.error("Translation unavailable")
        _answer_card(ui, result.error or "The text could not be translated.", "error")
        if english is not None and english.mode == "answered":
            ui.warning(
                "The English evidence is shown below for reference only. It is NOT a {} answer.".format(name)
            )
            _answer_card(ui, english.answer_text, "english", label="English evidence (not translated)")
            _render_sources(ui, english, translated=False)
        return

    ui.error("Error")
    _answer_card(ui, result.error or PROCESSING_ERROR_MESSAGE, "error")


# --------------------------------------------------------------------------
# Page layout
# --------------------------------------------------------------------------

_LEAF_SVG = (
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M20.6 3.4c-6.9-.6-12.4 1.3-14.9 '
    "5.3-1.9 3-1.6 6.5.2 8.9L3.5 20l1.4 1.4 2.4-2.4c2.4 1.8 5.9 2.1 8.9.2 4-2.5 5.9-8 5.3-14.9l-.9-.9z"
    'M8.8 16.6c2.1-3.9 5-6.6 8.6-8.4-3.1 2.4-5.4 5.2-7.1 8.9l-1.5-.5z"/></svg>'
)

_CSS = """
<style>
:root {
  --ag-forest: #14532D; --ag-emerald: #16804A; --ag-emerald-bright: #1f9a5c; --ag-cream: #F5FAF0;
  --ag-sage: #dfe9dc; --ag-sage-strong: #c4d6c0; --ag-mint: #f0f6ee;
  --ag-bg: #f7f5ef; --ag-surface: #ffffff; --ag-border: #e2e6dc;
  --ag-text: #183B2A; --ag-muted: #4f6558;
  --ag-amber: #8a5a12; --ag-amber-bg: #fbf4e4; --ag-amber-border: #ecd6a6;
  --ag-red: #9b2c24; --ag-red-bg: #fbecea; --ag-red-border: #efc4bf;
  --ag-radius: 16px; --ag-shadow: 0 1px 2px rgba(31,42,36,.05), 0 6px 20px rgba(31,42,36,.06);
}
/* Streamlit's bundled font has no Devanagari/Kannada glyphs; name the usual system fonts for them. */
[lang="hi"] { font-family: "Source Sans", "Nirmala UI", "Noto Sans Devanagari", "Mangal", sans-serif; }
[lang="kn"] { font-family: "Source Sans", "Nirmala UI", "Noto Sans Kannada", "Tunga", sans-serif; }
[data-testid="stAppViewContainer"] { background: transparent; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"], .block-container {
  max-width: 1100px; padding-top: 2.2rem; padding-bottom: 4rem;
}
[lang="hi"], [lang="kn"] { line-height: 1.75; }

/* Hero ---------------------------------------------------------------- */
.ag-hero {
  background: rgba(20,83,45,.80);
  -webkit-backdrop-filter: blur(16px); backdrop-filter: blur(16px);
  border: 1px solid rgba(255,255,255,.35);
  color: #fff; border-radius: 18px; padding: 2rem 2.2rem 1.8rem; box-shadow: 0 8px 32px rgba(15,45,25,.22);
  position: relative; overflow: hidden;
}
.ag-hero::after {
  content: ""; position: absolute; right: -60px; top: -60px; width: 240px; height: 240px;
  border-radius: 50%; background: rgba(255,255,255,.07);
}
.ag-brand { display: flex; align-items: center; gap: .6rem; font-weight: 700; font-size: 1.05rem; letter-spacing: .2px; }
.ag-brand-mark {
  width: 36px; height: 36px; border-radius: 10px; display: inline-flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,.16); color: #fff;
}
.ag-brand-mark svg { width: 21px; height: 21px; }
.ag-brand-tag { font-weight: 500; font-size: .78rem; opacity: .85; padding: .15rem .55rem; border: 1px solid rgba(255,255,255,.35); border-radius: 999px; }
.ag-hero h1 { color: #fff !important; font-size: 2.05rem; line-height: 1.2; margin: 1.1rem 0 .6rem; padding: 0; font-weight: 700; }
.ag-hero p { color: rgba(255,255,255,.9); font-size: 1.02rem; line-height: 1.6; margin: 0; max-width: 680px; }
.ag-chips { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1.2rem; }
.ag-chip { background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.22); color: #fff; font-size: .84rem; padding: .32rem .75rem; border-radius: 999px; }
.ag-hero--compact { padding: 1rem 1.4rem; border-radius: 18px; }
.ag-hero--compact .ag-brand { font-size: 1rem; }

/* Section labels ------------------------------------------------------- */
.ag-section { font-weight: 650; color: var(--ag-text); font-size: 1.02rem; margin: 1.6rem 0 .35rem; }
.ag-section-sub { color: var(--ag-muted); font-size: .9rem; margin: -.15rem 0 .6rem; }
.ag-lang-note { display: inline-flex; align-items: center; gap: .45rem; color: var(--ag-forest); background: var(--ag-mint);
  border: 1px solid var(--ag-sage-strong); border-radius: 999px; padding: .3rem .8rem; font-size: .86rem; margin: .5rem 0 0; }

/* Language selector (segmented control) ------------------------------- */
.st-key-language_label [data-testid="stButtonGroup"] { width: 100%; }
.st-key-language_label button {
  min-height: 48px; font-size: 1.05rem; flex: 1 1 0; border-color: var(--ag-sage-strong) !important;
  background: var(--ag-surface);
}
.st-key-language_label button[kind$="Active"], .st-key-language_label button[aria-checked="true"] {
  background: var(--ag-emerald) !important; color: #fff !important; border-color: var(--ag-emerald) !important;
}

/* Composer -------------------------------------------------------------- */
/* Frosted-glass panels: translucent light surface, blurred landscape behind, soft green edge. */
.st-key-lang_panel, .st-key-composer_panel, .st-key-suggest_panel, [class*="st-key-agent_turn_"] {
  background: rgba(245,250,240,.82);
  -webkit-backdrop-filter: blur(16px); backdrop-filter: blur(16px);
  border: 1px solid rgba(255,255,255,.55); border-radius: 18px;
  box-shadow: 0 8px 32px rgba(15,45,25,.16);
  padding: 1.5rem;
}
.st-key-lang_panel .ag-section, .st-key-composer_panel .ag-section, .st-key-suggest_panel .ag-section { margin-top: .1rem; }
.st-key-lang_panel, .st-key-composer_panel, .st-key-suggest_panel { margin-top: .9rem; }
[data-testid="stForm"] { background: transparent; border: none !important; box-shadow: none; padding: 0; }
.stTextArea [data-baseweb="textarea"], .stTextArea [data-baseweb="base-input"] {
  background: rgba(255,255,255,.90) !important; border: 1px solid rgba(40,110,70,.25) !important; border-radius: 14px !important;
}
.stTextArea textarea { font-size: 1.04rem; line-height: 1.6; border-radius: 14px; background: transparent !important; color: var(--ag-text); }
.stTextArea [data-baseweb="textarea"]:focus-within { border-color: var(--ag-emerald) !important; box-shadow: 0 0 0 2px rgba(22,128,74,.18); }
[data-testid="stForm"] button[kind^="primary"] {
  min-height: 48px; font-size: 1rem; font-weight: 600; border-radius: 12px; padding: 0 1.5rem;
  background: var(--ag-emerald); border: none; transition: background .15s ease, box-shadow .15s ease;
}
[data-testid="stForm"] button[kind^="primary"]:hover { background: var(--ag-forest); box-shadow: 0 4px 14px rgba(15,45,25,.25); }

/* Suggested questions --------------------------------------------------- */
.st-key-suggestions button {
  text-align: left; justify-content: flex-start; min-height: 56px; height: 100%; border-radius: 14px;
  background: rgba(255,255,255,.86); border: 1px solid rgba(40,110,70,.20); color: var(--ag-text);
  box-shadow: 0 2px 8px rgba(15,45,25,.08); line-height: 1.45; padding: .7rem .95rem;
  transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease, background .15s ease;
}
.st-key-suggestions button:hover {
  border-color: var(--ag-emerald); background: rgba(255,255,255,.96); color: var(--ag-forest);
  transform: translateY(-1px); box-shadow: 0 6px 16px rgba(15,45,25,.14);
}
.st-key-suggestions button p { font-size: .95rem; }
.st-key-suggestions button [data-testid="stMarkdownContainer"], .st-key-suggestions button p {
  white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
}

/* Conversation ---------------------------------------------------------- */
.ag-turn-user { display: flex; flex-direction: column; align-items: flex-end; margin: 1.4rem 0 .5rem; }
.ag-bubble {
  background: var(--ag-forest); color: #fff; padding: .8rem 1.05rem; border-radius: 18px 18px 4px 18px;
  max-width: 85%; font-size: 1.02rem; line-height: 1.55; box-shadow: var(--ag-shadow); word-wrap: break-word;
}
.ag-meta { color: rgba(255,255,255,.92); font-size: .78rem; margin-top: .3rem; text-shadow: 0 1px 6px rgba(6,28,18,.6); }
.ag-agent-label { display: flex; align-items: center; gap: .45rem; font-weight: 650; color: var(--ag-forest); font-size: .92rem; }
.ag-agent-label .ag-brand-mark { width: 26px; height: 26px; border-radius: 8px; background: var(--ag-mint); color: var(--ag-emerald); }
.ag-agent-label .ag-brand-mark svg { width: 16px; height: 16px; }


/* Status alerts restyled as compact badges ----------------------------- */
[class*="st-key-agent_turn_"] [data-testid="stAlert"] { display: inline-block; width: auto; }
[class*="st-key-agent_turn_"] [data-testid="stAlertContainer"] { padding: .35rem .8rem; border-radius: 999px; }
[class*="st-key-agent_turn_"] [data-testid="stAlertContainer"] p { font-size: .9rem; font-weight: 600; }

/* Answer cards ---------------------------------------------------------- */
.ag-answer { border-radius: 14px; padding: .95rem 1.1rem; margin: .35rem 0 .5rem; font-size: 1.04rem; line-height: 1.7; color: var(--ag-text); word-wrap: break-word; }
.ag-answer-label { font-size: .76rem; font-weight: 700; text-transform: uppercase; letter-spacing: .6px; margin-bottom: .35rem; }
.ag-answer--evidence { background: var(--ag-mint); border-left: 4px solid var(--ag-emerald); }
.ag-answer--evidence .ag-answer-label { color: var(--ag-emerald); }
.ag-answer--english { background: #f6f7f4; border-left: 4px solid var(--ag-sage-strong); font-size: .97rem; }
.ag-answer--english .ag-answer-label { color: var(--ag-muted); }
.ag-answer--abstain { background: var(--ag-amber-bg); border: 1px solid var(--ag-amber-border); color: #4d3a14; }
.ag-answer--error { background: var(--ag-red-bg); border: 1px solid var(--ag-red-border); color: #5a1d18; }
.ag-tip { color: var(--ag-muted); font-size: .9rem; margin: .1rem 0 .4rem; }

/* Sources --------------------------------------------------------------- */
.ag-sources-head { display: flex; align-items: baseline; gap: .6rem; margin: 1rem 0 .4rem; border-top: 1px solid var(--ag-border); padding-top: .9rem; }
.ag-sources-title { font-weight: 700; font-size: 1rem; color: var(--ag-text); }
.ag-sources-count { color: var(--ag-muted); font-size: .85rem; }
.ag-source { border: 1px solid var(--ag-border); border-radius: 14px; padding: .8rem .95rem; margin: .5rem 0; background: #fcfdfb; }
.ag-source-head { display: flex; align-items: flex-start; gap: .7rem; }
.ag-source-num { flex: 0 0 28px; height: 28px; border-radius: 8px; background: var(--ag-sage); color: var(--ag-forest); font-weight: 700; display: inline-flex; align-items: center; justify-content: center; font-size: .88rem; }
.ag-source-meta { flex: 1 1 auto; min-width: 0; }
.ag-source-title { font-weight: 650; color: var(--ag-text); line-height: 1.4; }
.ag-source-org { color: var(--ag-muted); font-size: .86rem; line-height: 1.4; margin-top: .1rem; }
.ag-page { flex: 0 0 auto; background: var(--ag-forest); color: #fff; font-size: .8rem; font-weight: 650; padding: .22rem .6rem; border-radius: 999px; white-space: nowrap; }
.ag-excerpt { margin: .6rem 0 .2rem 2.35rem; }
.ag-excerpt summary { cursor: pointer; color: var(--ag-emerald); font-weight: 600; font-size: .9rem; padding: .3rem 0; }
.ag-excerpt-text { font-size: .9rem; line-height: 1.6; color: #3a4740; background: #f4f6f1; border-radius: 10px; padding: .7rem .85rem; margin-top: .3rem; max-height: 320px; overflow-y: auto; }
.ag-source-link { display: inline-block; margin: .45rem 0 0 2.35rem; color: var(--ag-forest) !important; font-weight: 600; font-size: .9rem; text-decoration: none; border-bottom: 1px solid var(--ag-sage-strong); }
.ag-source-link:hover { border-bottom-color: var(--ag-forest); }

/* Sidebar and footer ---------------------------------------------------- */
[data-testid="stSidebar"] {
  background: rgba(245,250,240,.88); -webkit-backdrop-filter: blur(16px); backdrop-filter: blur(16px);
  border-right: 1px solid rgba(255,255,255,.55);
}
[data-testid="stSidebar"] h2 { color: var(--ag-forest); }
/* On tablets the default 300px sidebar would take over a third of the screen. */
@media (max-width: 1024px) {
  [data-testid="stSidebar"][aria-expanded="true"] { width: 230px !important; min-width: 230px !important; }
  [data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-left: .3rem; padding-right: .3rem; }
}
.ag-footer {
  text-align: center; color: #34463c; font-size: .84rem; margin-top: 1.6rem; line-height: 1.6; padding: .8rem 1.1rem;
  background: rgba(245,250,240,.82); border: 1px solid rgba(255,255,255,.55); border-radius: 18px;
  -webkit-backdrop-filter: blur(16px); backdrop-filter: blur(16px); box-shadow: 0 8px 32px rgba(15,45,25,.16);
}

/* Small screens ---------------------------------------------------------- */
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"], .block-container { padding-left: .85rem; padding-right: .85rem; padding-top: 1.2rem; }
  .ag-hero { padding: 1.4rem 1.25rem 1.3rem; border-radius: 18px; }
  .ag-hero h1 { font-size: 1.55rem; }
  .ag-hero p { font-size: .96rem; }
  .ag-bubble { max-width: 94%; }
  .ag-brand-tag { display: none; }
  .st-key-lang_panel, .st-key-composer_panel, .st-key-suggest_panel, [class*="st-key-agent_turn_"] { padding: 1rem; border-radius: 16px; }
  .ag-excerpt, .ag-source-link { margin-left: 0; }
  .ag-source-head { flex-wrap: wrap; }
  .st-key-language_label button { font-size: 1rem; padding-left: .4rem; padding-right: .4rem; }
}
</style>
"""


ASSETS_DIR = ROOT / "assets"
PAGE_BACKGROUND = "agriguide_background.webp"

# The AI-generated background image (1672 x 941) is embedded once as a data URI: Streamlit does not serve
# arbitrary project folders, and a relative "../assets" URL would not resolve in the browser. The
# image is painted on a fixed, viewport-sized layer behind the app with background-size: cover, so
# it fills any screen without distortion while the page scrolls above it. A fixed layer is used
# instead of background-attachment: fixed because mobile browsers handle the latter badly. On
# portrait screens the crop is moved to the right, which keeps the sun, canal and hills in view.
_PAGE_BACKGROUND_CSS = """
<style>
:root { --ag-page-image: url("__IMAGE__"); }
[data-testid="stApp"] { min-height: 100vh; background: #1d4a35; }
[data-testid="stApp"]::before {
  content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background-image: linear-gradient(rgba(15,45,25,.12), rgba(15,45,25,.12)), var(--ag-page-image);
  background-size: cover; background-position: center center; background-repeat: no-repeat;
}
[data-testid="stAppViewContainer"], [data-testid="stSidebar"], [data-testid="stHeader"] { position: relative; z-index: 1; }
@media (max-aspect-ratio: 1/1) {
  [data-testid="stApp"]::before { background-position: 80% center; }
}
</style>
"""


@functools.lru_cache(maxsize=1)
def _page_background_css() -> str:
    """CSS that paints the saved background image behind the page; empty if the file is missing."""
    try:
        raw = (ASSETS_DIR / PAGE_BACKGROUND).read_bytes()
    except OSError:
        LOGGER.warning("Page background %s not found; using the plain green background", PAGE_BACKGROUND)
        return ""
    uri = "data:image/webp;base64," + base64.b64encode(raw).decode("ascii")
    return _PAGE_BACKGROUND_CSS.replace("__IMAGE__", uri)


def _render_hero(compact: bool) -> None:
    brand = (
        '<div class="ag-brand"><span class="ag-brand-mark">{}</span>AgriGuide AI'
        '<span class="ag-brand-tag">Evidence-grounded crop advisory</span></div>'.format(_LEAF_SVG)
    )
    if compact:
        st.markdown('<div class="ag-hero ag-hero--compact">{}</div>'.format(brand), unsafe_allow_html=True)
        return
    st.markdown(
        '<div class="ag-hero">{brand}'
        "<h1>Crop guidance you can trace back to the source</h1>"
        "<p>Ask about irrigation, fertilizer, sowing, plant protection or drone spraying. "
        "AgriGuide AI searches official crop production guides, quotes the passage that "
        "answers you and shows the exact page it came from. When the guides do not cover "
        "your question, it says so instead of guessing.</p>"
        '<div class="ag-chips">'
        '<span class="ag-chip">3 official source documents</span>'
        '<span class="ag-chip">Page-level citations</span>'
        '<span class="ag-chip">English · हिन्दी · ಕನ್ನಡ</span>'
        "</div></div>".format(brand=brand),
        unsafe_allow_html=True,
    )


def _render_sidebar() -> None:
    with st.sidebar:
        st.header("About this project")
        st.write(
            "AgriGuide AI is a university project using multilingual E5, a "
            "saved FAISS index, and deterministic extractive evidence."
        )
        st.caption(
            "Answers quote retrieved text. The application does not use an LLM "
            "to generate agricultural recommendations."
        )
        st.caption(
            "Hindi and Kannada use automatic IndicTrans2 translation of the question "
            "and of the English answer. Source excerpts always stay in English."
        )
        st.caption(
            "Model limitation: the project specification names the BharatGen AgriParam "
            "language model. It was tested but is not used, because its answers were "
            "not accurate enough in our tests (for example, wrong fertilizer rates). "
            "This app therefore only quotes source text, and that requirement is not "
            "met. Check any quantity or timing against the cited source page, and ask "
            "an agricultural expert before acting."
        )
        if st.session_state.get("history"):
            st.button("Clear conversation", on_click=_clear_history, width="stretch")


def _queue_question(question: str, language: str) -> None:
    st.session_state["pending_question"] = (question, language)


def _clear_history() -> None:
    st.session_state["history"] = []


def _question_text(result) -> str:
    return result.original_question if isinstance(result, MultilingualResult) else result.question


def _render_turn(entry: dict) -> None:
    language, result = entry["language"], entry["result"]
    label = next(name for name, code in LANGUAGE_OPTIONS.items() if code == language)
    st.markdown(
        '<div class="ag-turn-user"><div class="ag-bubble" lang="{}">{}</div>'
        '<div class="ag-meta">You · {}</div></div>'.format(_attr(language), _esc(_question_text(result)), _esc(label)),
        unsafe_allow_html=True,
    )
    with st.container(key="agent_turn_{}".format(entry["id"])):
        st.markdown(
            '<div class="ag-agent-label"><span class="ag-brand-mark">{}</span>AgriGuide AI</div>'.format(_LEAF_SVG),
            unsafe_allow_html=True,
        )
        if isinstance(result, MultilingualResult):
            render_multilingual_result(st, result)
        else:
            render_result(st, result)


def _answer(question: str, language: str):
    """Run one question through the existing pipeline (English direct, hi/kn translated)."""
    if language == "en":
        with st.spinner("Searching the source documents…"):
            return submit_question(_load_pipeline(), question)
    with st.spinner(
        "Translating and searching. The first {} question loads the "
        "translation models and can take a minute…".format(LANGUAGE_NAMES[language])
    ):
        return submit_multilingual_question(_load_pipeline(), _load_translator(), question, language)


def main() -> None:
    st.set_page_config(
        page_title="AgriGuide AI",
        page_icon="🌱",
        layout="centered",
        initial_sidebar_state="auto",
    )
    st.markdown(_CSS + _page_background_css(), unsafe_allow_html=True)
    history: list = st.session_state.setdefault("history", [])

    _render_sidebar()
    # Filled at the end of the run, once this run's question (if any) is in the history.
    hero = st.empty()

    with st.container(key="lang_panel"):
        st.markdown('<div class="ag-section">Choose your language</div>', unsafe_allow_html=True)
        language_label = st.segmented_control(
            "Language (question and answer)",
            options=list(LANGUAGE_OPTIONS),
            default="English",
            required=True,
            key="language_label",
            label_visibility="collapsed",
            width="stretch",
        )
        language = LANGUAGE_OPTIONS[language_label]
        if language == "en":
            note = "Ask and read answers in English."
        else:
            note = "Ask in {label} ({name}). Your question and the answer are translated automatically with IndicTrans2.".format(
                label=language_label, name=LANGUAGE_NAMES[language]
            )
        st.markdown('<div class="ag-lang-note">{}</div>'.format(_esc(note)), unsafe_allow_html=True)

    thread = st.container()

    examples = SUGGESTED_QUESTIONS[language]
    with st.container(key="composer_panel"):
        composer_heading = st.empty()
        with st.form("question_form", clear_on_submit=True, border=False):
            typed = st.text_area(
                "Agricultural question",
                placeholder="For example: {}".format(examples[0][1]),
                height=110,
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("Ask AgriGuide", type="primary")
        composer_notice = st.empty()

    with st.container(key="suggest_panel"):
        st.markdown('<div class="ag-section">Try a question</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="ag-section-sub">Tap one to ask it now. Answers come from the source documents.</div>',
            unsafe_allow_html=True,
        )
        with st.container(key="suggestions"):
            # One row of columns per pair, so small screens stack them in reading order.
            for row in range(0, len(examples), 2):
                for column, number in zip(st.columns(2), range(row, min(row + 2, len(examples)))):
                    topic, text = examples[number]
                    column.button(
                        "**{}** · {}".format(topic, text),
                        key="suggest_{}_{}".format(language, number),
                        on_click=_queue_question,
                        args=(text, language),
                        width="stretch",
                    )

    pending = st.session_state.pop("pending_question", None)
    question = ""
    if pending is not None:
        question, language = pending
    elif submitted:
        question = typed
        if not question.strip():
            composer_notice.warning("Enter an agricultural question to continue.")

    with thread:
        for entry in history:
            _render_turn(entry)
        if question.strip():
            try:
                result = _answer(question, language)
            except ApplicationBootstrapError as exc:
                st.error("AgriGuide AI could not start: {}".format(exc))
            except Exception as exc:
                LOGGER.error("Application request failed (%s)", type(exc).__name__)
                st.error(PROCESSING_ERROR_MESSAGE)
            else:
                # A per-session counter keeps container keys unique after old turns are trimmed.
                entry_id = st.session_state.get("next_turn_id", 0)
                st.session_state["next_turn_id"] = entry_id + 1
                history.append({"id": entry_id, "language": language, "result": result})
                del history[:-MAX_HISTORY]
                _render_turn(history[-1])

    with hero.container():
        _render_hero(compact=bool(history))
    composer_heading.markdown(
        '<div class="ag-section">{}</div>'.format("Ask another question" if history else "Ask your question"),
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="ag-footer">AgriGuide AI quotes official crop production guides and shows every source page. '
        "It does not replace an agricultural expert; check quantities and timings with your local "
        "Krishi Vigyan Kendra before acting.</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
