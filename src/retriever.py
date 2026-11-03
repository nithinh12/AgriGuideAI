"""FAISS-backed retrieval with an abstention gate.

Uses ``faiss.IndexFlatIP`` (exact inner-product search) over L2-normalized
embeddings, which equals cosine similarity. Exact search is affordable at
this project's scale (hundreds to low thousands of chunks) and is fully
deterministic — no ANN recall randomness in evaluation.

The ``min_score`` gate is what enables honest abstention: when no candidate
passes the threshold, the pipeline reports insufficient evidence instead of
forcing a top-k answer from unrelated text.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import faiss
import numpy as np

from src.text_chunker import Chunk


_TOKEN_RE = re.compile(r"\d+(?:\.\d+)?%?|[a-z]+", re.IGNORECASE)
_STOP_WORDS = frozenset(
    "a an and are as at be been before between by can does for from give given "
    "has have how in into is it listed me my of on or should the this to use "
    "was were what when where which who why with would guide recommend "
    "recommendation advised state say says tell please about according provide "
    "provided after during does do i we you your they their using used use "
    # Quantity and degree phrasing ("how much", "per hectare", "the most")
    # asks for an amount or an extreme; it names nothing a passage must contain.
    "much many per more most".split()
)
_TOKEN_CANONICAL = {
    "paddy": "rice",
    "paddies": "rice",
    "rice": "rice",
    "maize": "maize",
    "corn": "maize",
    "grapes": "grape",
    "grape": "grape",
    "vines": "grape",
    "vine": "grape",
    "fertiliser": "fertilizer",
    "fertilisers": "fertilizer",
    "fertilizers": "fertilizer",
    "irrigation": "irrigate",
    "irrigations": "irrigate",
    "irrigate": "irrigate",
    "irrigated": "irrigate",
    "irrigating": "irrigate",
    # Verb forms of applying water to a crop ("when should wheat be watered?").
    # Plain "water" is left alone: it also means water bodies, spray volume, etc.
    "watered": "irrigate",
    "watering": "irrigate",
    "spray": "spray",
    "sprays": "spray",
    "spraying": "spray",
    "sprayed": "spray",
    "pesticides": "pesticide",
    "pesticide": "pesticide",
    "drones": "drone",
    "drone": "drone",
    "precautions": "precaution",
    "precaution": "precaution",
    "safety": "safety",
    "safe": "safety",
    # Spelling, synonym and inflection variants that the guides and the
    # machine-translated questions use interchangeably. Without them a passage
    # that says "Apply gypsum ... Pegging ... phases are critical" shares too
    # few terms with "How much gypsum should be applied ... growth stages".
    "peanut": "groundnut",
    "peanuts": "groundnut",
    "groundnuts": "groundnut",
    "soyabean": "soybean",
    "soyabeans": "soybean",
    "phase": "stage",
    "phases": "stage",
    "hectare": "ha",
    "hectares": "ha",
    # Only the -ing forms the guides actually pair with a base verb. A general
    # -ing stemmer was tried and rejected: it turns "standing water" into
    # "stand", which then matches "crop stand" (plant population).
    "cutting": "cut",
    "ratooning": "ratoon",
    "applied": "apply",
    "applies": "apply",
    "applying": "apply",
    "stagnation": "stagnate",
    "stagnates": "stagnate",
    "stagnated": "stagnate",
    "stagnating": "stagnate",
    "stagnant": "stagnate",
}
# Two-letter unit tokens that carry meaning ("kg/ha") despite the length filter.
_UNIT_TOKENS = frozenset({"ha"})
_CROP_ALIASES = {
    "maize": frozenset({"maize", "corn"}),
    "wheat": frozenset({"wheat"}),
    # Without an entry a crop is not enforced, so another crop's sowing or
    # irrigation text could answer a sorghum question.
    "sorghum": frozenset({"sorghum"}),
    "rice": frozenset({"rice", "paddy"}),
    # "Vine" is ambiguous (for example betelvine); require an explicit grape
    # mention to avoid treating unrelated vine crops as grape evidence.
    "grape": frozenset({"grape", "grapes"}),
    "tomato": frozenset({"tomato", "tomatoes"}),
    "mango": frozenset({"mango", "mangoes"}),
    "cotton": frozenset({"cotton"}),
    "groundnut": frozenset({"groundnut", "peanut", "peanuts"}),
    "soybean": frozenset({"soybean", "soybeans", "soy"}),
    "sugarcane": frozenset({"sugarcane"}),
    "pigeon pea": frozenset({"pigeon", "pea", "pigeonpea"}),
}
_AGRICULTURE_ANCHORS = frozenset(
    {
        "agriculture", "agricultural", "crop", "farm", "farming", "farmer",
        "field", "soil", "water", "moisture", "irrigate", "fertilizer",
        "manure", "nutrient", "seed", "sow", "plant", "harvest", "pesticide",
        "insecticide", "fungicide", "pest", "weed", "disease", "spray", "drone",
        "horticulture", "fruit", "vegetable", "maize", "wheat", "rice", "grape",
        "tomato", "mango", "cotton", "groundnut", "soybean", "sugarcane",
        "nursery", "yield", "cultivation", "compost", "npk", "pump", "subsidy",
        "solar", "rainfall", "irrigation", "fodder", "orchard", "vineyard",
    }
)
_GENERIC_AGRICULTURE_TERMS = frozenset(
    {
        "guide", "sop", "kisan", "application", "recommend", "recommendation",
        "advice", "listed", "section", "covered", "include", "provide",
        "specific", "management", "agricultural", "agriculture",
        # Question phrasing ("is it recommended", "does the crop need", "which
        # list") says what kind of answer is wanted, not which evidence is
        # needed. These still count toward query coverage when a passage has
        # them, but a passage is not required to contain them.
        "recommended", "recommending", "need", "needed", "list", "listing",
    }
)
# Interrogative boilerplate such as "under what conditions" asks for any
# conditions; it names none. A concrete condition ("under saline conditions",
# "soil conditions") has no what/which and stays a meaningful term.
_CONDITION_QUESTION_RE = re.compile(
    r"\b(?:under|in)\s+(?:what|which)\s+conditions?\b", re.IGNORECASE
)
# "water" is irrigation only as a verb whose object is a crop: "when to water
# wheat", "should I water the rice". Nouns and other uses ("water bodies",
# "water for spray volume", "water management") are not matched and stay as
# the plain term "water".
_WATER_CROP_VERB_RE = re.compile(
    r"(?P<lead>\b(?:to|should|do|does|can|must|will)\s+(?:(?:i|we|you|one|farmers?)\s+)?)"
    r"water"
    r"(?P<tail>\s+(?:the\s+|my\s+|our\s+)?(?:"
    + "|".join(sorted({a for aliases in _CROP_ALIASES.values() for a in aliases}, key=len, reverse=True))
    + r")\b)",
    re.IGNORECASE,
)
_CONTEXT_PHRASES = (
    "before planting",
    "less fertile",
    "saline soil",
    "saline soils",
    "acid soil",
    "acid soils",
    "light textured soil",
    "heavy soil",
    "heavy soils",
    "soil test",
)
_CURRENT_DATA_RE = re.compile(
    r"\b(today|tomorrow|currently|current|latest|right now|this week|this month|"
    r"this season|\d{4}[-/]\d{2,4})\b",
    re.IGNORECASE,
)
# A question term that occurs in no indexed chunk (a crop, product or place the
# knowledge base never mentions) can never be matched by any passage. When one
# is present, a passage must still cover at least this share of the
# rarity-weighted discriminating terms, with the unknown term counted as
# unmatched, so common words such as "spacing" or "plant" cannot stand in for
# the missing subject.
UNKNOWN_TERM_MIN_COVERAGE = 0.5
_MEASUREMENT_RE = re.compile(
    r"(?<![a-z])\d+(?:\.\d+)?\s*(?:%|kg/?ha|kg/?acre|g/?ha|g/?l|mg/?l|"
    r"mm|cm|m|ha|acre|days?|weeks?|months?)?\b",
    re.IGNORECASE,
)


def content_terms(text: str) -> tuple[str, ...]:
    """Return normalized query/content terms, excluding question boilerplate."""
    terms: list[str] = []
    text = _CONDITION_QUESTION_RE.sub(" ", text)
    text = _WATER_CROP_VERB_RE.sub(r"\g<lead>irrigate\g<tail>", text)
    for raw in _TOKEN_RE.findall(text.lower()):
        if raw in _STOP_WORDS or (
            len(raw) < 3 and not raw.isdigit() and raw not in _UNIT_TOKENS
        ):
            continue
        canonical = _TOKEN_CANONICAL.get(raw, raw)
        if raw in _TOKEN_CANONICAL:
            pass
        elif raw.endswith("ies") and len(raw) > 4:
            canonical = raw[:-3] + "y"
        elif raw.endswith("s") and len(raw) > 4:
            canonical = raw[:-1]
        if canonical not in terms:
            terms.append(canonical)
    return tuple(terms)


def crop_anchors(text: str) -> frozenset[str]:
    """Find explicit crop names so evidence for one crop cannot answer another."""
    words = {word.lower() for word in _TOKEN_RE.findall(text)}
    anchors = set()
    for crop, aliases in _CROP_ALIASES.items():
        if crop == "pigeon pea":
            if {"pigeon", "pea"}.issubset(words) or "pigeonpea" in words:
                anchors.add(crop)
        elif words.intersection(aliases):
            anchors.add(crop)
    return frozenset(anchors)


def query_specific_terms(text: str) -> frozenset[str]:
    """Terms that distinguish a question from broad agriculture prose."""
    return frozenset(content_terms(text)) - _AGRICULTURE_ANCHORS - _GENERIC_AGRICULTURE_TERMS


def _lexical_tokens(text: str) -> tuple[str, ...]:
    return content_terms(text)


@dataclass(frozen=True)
class RetrievedPassage:
    """One retrieved chunk with its cosine similarity score."""

    chunk: Chunk
    score: float
    lexical_score: float = 0.0
    fused_score: float = 0.0
    matched_terms: tuple[str, ...] = ()
    term_coverage: float = 0.0
    # True when the requested crop is not named in this chunk and was taken
    # from the immediately preceding chunk (see ``FaissRetriever.crop_context``).
    crop_context_inherited: bool = False


class FaissRetriever:
    """Exact cosine-similarity retriever with a minimum-score gate."""

    def __init__(self, dimension: int, min_score: float = 0.40):
        if dimension <= 0:
            raise ValueError(f"dimension must be positive, got {dimension}")
        self.dimension = dimension
        self.min_score = min_score
        self._index = faiss.IndexFlatIP(dimension)
        self._chunks: list[Chunk] = []
        self._chunk_positions: dict[str, int] = {}
        self._lexical_documents: list[tuple[str, ...]] = []
        self._document_frequencies: dict[str, int] = {}
        self._average_document_length = 0.0

    @property
    def size(self) -> int:
        return len(self._chunks)

    def add(self, embeddings: np.ndarray, chunks: list[Chunk]) -> None:
        """Add embeddings (float32, L2-normalized) paired with their chunks."""
        if embeddings.ndim != 2 or embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"expected embeddings of shape (n, {self.dimension}), "
                f"got {embeddings.shape}"
            )
        if embeddings.shape[0] != len(chunks):
            raise ValueError(
                f"embedding/chunk count mismatch: {embeddings.shape[0]} vs {len(chunks)}"
            )
        if embeddings.shape[0] == 0:
            return
        self._index.add(np.asarray(embeddings, dtype=np.float32))
        for offset, chunk in enumerate(chunks, start=len(self._chunks)):
            self._chunk_positions[chunk.chunk_id] = offset
        self._chunks.extend(chunks)
        self._lexical_documents.extend(_lexical_tokens(chunk.text) for chunk in chunks)
        self._rebuild_lexical_statistics()

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        query_text: str | None = None,
    ) -> list[RetrievedPassage]:
        """Return top-k passages with score >= min_score, best first."""
        if query_text is not None:
            return self.search_hybrid(query_embedding, query_text, top_k=top_k)
        if top_k <= 0:
            raise ValueError(f"top_k must be positive, got {top_k}")
        if self.size == 0:
            return []

        query = np.asarray(query_embedding, dtype=np.float32).reshape(1, -1)
        scores, indices = self._index.search(query, min(top_k, self.size))
        results: list[RetrievedPassage] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:  # faiss pads with -1 when fewer candidates exist
                continue
            value = float(score)
            if value < self.min_score:
                continue
            results.append(RetrievedPassage(chunk=self._chunks[int(idx)], score=value))
        return results

    def search_lexical(self, query_text: str, top_k: int = 5) -> list[RetrievedPassage]:
        """Return a BM25 ranking over the already-loaded chunk manifest."""
        if top_k <= 0:
            raise ValueError(f"top_k must be positive, got {top_k}")
        if not self.size:
            return []
        terms = content_terms(query_text)
        if not terms:
            return []
        scores = self._bm25_scores(terms)
        ordered = sorted(range(self.size), key=lambda index: (-scores[index], index))
        return [
            RetrievedPassage(
                chunk=self._chunks[index],
                score=0.0,
                lexical_score=scores[index],
                matched_terms=tuple(
                    term for term in terms if term in set(self._lexical_documents[index])
                ),
                term_coverage=self._term_coverage(terms, self._lexical_documents[index]),
            )
            for index in ordered[:top_k]
            if scores[index] > 0.0
        ]

    def search_hybrid(
        self,
        query_embedding: np.ndarray,
        query_text: str,
        top_k: int = 5,
        rrf_constant: int = 60,
        candidate_pool: int = 100,
        lexical_weight: float = 2.0,
    ) -> list[RetrievedPassage]:
        """Fuse dense cosine and BM25 ranks with reciprocal-rank fusion.

        The saved FAISS vectors are only read. Lexical statistics are rebuilt
        in memory from the associated chunk manifest.
        """
        if top_k <= 0:
            raise ValueError(f"top_k must be positive, got {top_k}")
        if rrf_constant <= 0:
            raise ValueError("rrf_constant must be positive")
        if lexical_weight <= 0:
            raise ValueError("lexical_weight must be positive")
        if not self.size:
            return []

        query = np.asarray(query_embedding, dtype=np.float32).reshape(1, -1)
        if query.shape[1] != self.dimension:
            raise ValueError(
                f"expected query dimension {self.dimension}, got {query.shape[1]}"
            )
        dense_scores, dense_indices = self._index.search(query, self.size)
        dense_order = [int(index) for index in dense_indices[0] if index >= 0]
        terms = content_terms(query_text)
        lexical_scores = self._bm25_scores(terms)
        lexical_order = [
            index
            for index in sorted(
                range(self.size), key=lambda item: (-lexical_scores[item], item)
            )
            if lexical_scores[index] > 0.0
        ]

        dense_rank = {index: rank for rank, index in enumerate(dense_order, start=1)}
        dense_score_by_index = {
            index: float(dense_scores[0][rank - 1])
            for index, rank in dense_rank.items()
        }
        lexical_rank = {index: rank for rank, index in enumerate(lexical_order, start=1)}
        pool = set(dense_order[:candidate_pool]) | set(lexical_order[:candidate_pool])
        fused = {
            index: (
                (1.0 / (rrf_constant + dense_rank[index]) if index in dense_rank else 0.0)
                + (
                    lexical_weight / (rrf_constant + lexical_rank[index])
                    if index in lexical_rank
                    else 0.0
                )
            )
            for index in pool
        }
        ordered = sorted(
            pool,
            key=lambda index: (
                -fused[index],
                -lexical_scores[index],
                -dense_score_by_index[index],
                index,
            ),
        )
        query_set = set(terms)
        results: list[RetrievedPassage] = []
        for index in ordered:
            dense_score = dense_score_by_index[index]
            if dense_score < self.min_score:
                continue
            document_terms = self._lexical_documents[index]
            matched = tuple(term for term in terms if term in set(document_terms))
            results.append(
                RetrievedPassage(
                    chunk=self._chunks[index],
                    score=dense_score,
                    lexical_score=lexical_scores[index],
                    fused_score=fused[index],
                    matched_terms=matched,
                    term_coverage=(len(set(matched) & query_set) / len(query_set))
                    if query_set
                    else 0.0,
                )
            )
            if len(results) >= top_k:
                break
        return results

    def relevant_evidence(
        self, query_text: str, passages: list[RetrievedPassage]
    ) -> tuple[list[RetrievedPassage], str | None]:
        """Keep passages with query support, crop agreement, and answerable scope."""
        if _CURRENT_DATA_RE.search(query_text):
            return [], "The question asks for current or local information absent from the indexed sources."

        terms = set(content_terms(query_text))
        if not terms:
            return [], "The question has no identifiable agricultural evidence terms."

        if not (terms & _AGRICULTURE_ANCHORS) and not crop_anchors(query_text):
            return [], "The question is outside the agricultural topics covered by this knowledge base."

        requested_crops = crop_anchors(query_text)
        specific_terms = query_specific_terms(query_text)
        normalized_query = re.sub(r"[^a-z0-9]+", " ", query_text.lower()).strip()
        required_context = tuple(
            phrase for phrase in _CONTEXT_PHRASES if phrase in normalized_query
        )
        requires_preplant_watering = (
            "before planting" in normalized_query
            and bool(terms & {"water", "irrigate"})
        )
        requested_values = {
            value.strip().lower()
            for value in _MEASUREMENT_RE.findall(query_text)
            if value.strip() and any(character.isdigit() for character in value)
        }
        unknown_terms = sorted(
            term
            for term in specific_terms
            if not any(character.isdigit() for character in term)
            and not self._document_frequencies.get(term)
        )
        term_weights = {term: self._idf(term) for term in specific_terms}
        rejected_for_unknown_terms = False
        accepted: list[RetrievedPassage] = []
        for passage in passages:
            passage_text = passage.chunk.text
            normalized_passage = re.sub(r"[^a-z0-9]+", " ", passage_text.lower())
            if any(phrase not in normalized_passage for phrase in required_context):
                continue
            if requires_preplant_watering:
                # Do not combine a planting reference in one list item with
                # irrigation guidance in another. The indexed evidence must
                # explicitly support watering before planting in the same
                # sentence or bullet. Water used to prepare a slurry or
                # solution is not evidence of irrigating the planting ground.
                clauses = re.split(r"(?<=[.!?])\s+|[•\uF0B7\uFFFD]+", passage_text)
                if not any(
                    re.search(r"\bbefore\s+planting\b", clause, re.IGNORECASE)
                    and re.search(
                        r"\b(?:irrigat\w*|watering)\b|\bwater(?:ed|ing)?\s+"
                        r"(?:the\s+)?(?:ground|soil|field|bed|land)\b",
                        clause,
                        re.IGNORECASE,
                    )
                    for clause in clauses
                ):
                    continue
            if re.search(r"\bcontents\b", passage_text, re.IGNORECASE) and re.search(
                r"\bpage\s*no\b", passage_text, re.IGNORECASE
            ):
                # A table of contents can repeat topic headings without
                # containing the supporting guidance itself.
                continue
            passage_terms = set(_lexical_tokens(passage.chunk.text))
            inherited = False
            if requested_crops:
                context, inherited = self.crop_context(passage.chunk)
                if not requested_crops.issubset(context):
                    continue
            matched = terms & passage_terms
            if len(matched) < min(2, len(terms)):
                continue
            coverage = len(matched) / len(terms)
            if len(terms) >= 4 and coverage < 0.30:
                continue
            # Broad agriculture terms can make an introductory paragraph look
            # relevant to a specific safety, rate, or management question.
            # Require at least two of the query's discriminating terms when
            # the query contains at least two such terms.
            specific_matches = specific_terms & passage_terms
            if len(specific_terms) >= 2 and len(specific_matches) < 2:
                continue
            if specific_terms and not specific_matches:
                continue
            if unknown_terms and (
                sum(term_weights[term] for term in specific_matches)
                < UNKNOWN_TERM_MIN_COVERAGE * sum(term_weights.values())
            ):
                rejected_for_unknown_terms = True
                continue
            if {"time", "day"}.issubset(terms) and not re.search(
                r"\b(morning|evening|afternoon|night|daytime)\b",
                passage_text,
                re.IGNORECASE,
            ):
                continue
            if "which" in query_text.lower() and "crop" in terms:
                if len(crop_anchors(passage.chunk.text)) < 2:
                    continue
            if requested_values and not requested_values.issubset(
                {value.strip().lower() for value in _MEASUREMENT_RE.findall(passage.chunk.text)}
            ):
                continue
            accepted.append(
                replace(passage, crop_context_inherited=True) if inherited else passage
            )

        if accepted:
            if len(accepted) > 1 and specific_terms:
                # Accepted passages keep their fused order, so a passage that
                # covers every discriminating term can sit behind several that
                # cover only some, and fall outside the top-k that answers are
                # drawn from. Stable sort: ties keep the fused order.
                total_weight = sum(term_weights.values())

                def covered_share(passage: RetrievedPassage) -> float:
                    present = specific_terms & set(_lexical_tokens(passage.chunk.text))
                    return round(sum(term_weights[term] for term in present) / total_weight, 2)

                accepted.sort(key=lambda passage: -covered_share(passage))
            return accepted, None
        if rejected_for_unknown_terms:
            return [], (
                "The question mentions terms that appear nowhere in the knowledge base "
                "({}), and no retrieved passage covers the rest of the question well "
                "enough to answer it.".format(", ".join(unknown_terms))
            )
        if requested_crops:
            return [], "No retrieved passage supports both the requested crop and the question's key terms."
        return [], "Retrieved passages do not share enough key terms with the question to support an answer."

    def crop_context(self, chunk: Chunk) -> tuple[frozenset[str], bool]:
        """Crops a chunk is about, and whether they were inherited.

        A chunk normally names its crop. Chunk boundaries fall mid-section,
        though: the groundnut "Water management" step can start a chunk that
        never repeats the word "groundnut" (the heading is on the previous
        page, and the PDF even splits "Gr oundnut"). When a chunk names no crop
        at all, the crops named by the chunk directly before it (same document,
        same or previous page) are used. One hop only: context is never chained
        across several chunks, and a chunk that names any crop keeps its own.
        """
        own = crop_anchors(chunk.text)
        if own:
            return own, False
        position = self._chunk_positions.get(chunk.chunk_id)
        if not position:
            return frozenset(), False
        previous = self._chunks[position - 1]
        if previous.doc_id != chunk.doc_id or chunk.page_number - previous.page_number not in (0, 1):
            return frozenset(), False
        inherited = crop_anchors(previous.text)
        return inherited, bool(inherited)

    def _idf(self, term: str) -> float:
        frequency = self._document_frequencies.get(term, 0)
        return math.log(1.0 + (self.size - frequency + 0.5) / (frequency + 0.5))

    def _rebuild_lexical_statistics(self) -> None:
        frequencies: dict[str, int] = {}
        for document in self._lexical_documents:
            for term in set(document):
                frequencies[term] = frequencies.get(term, 0) + 1
        self._document_frequencies = frequencies
        self._average_document_length = (
            sum(len(document) for document in self._lexical_documents) / self.size
            if self.size
            else 0.0
        )

    def _bm25_scores(self, terms: tuple[str, ...]) -> list[float]:
        if not terms or not self.size:
            return [0.0] * self.size
        k1 = 1.5
        b = 0.75
        average_length = max(self._average_document_length, 1.0)
        scores: list[float] = []
        for document in self._lexical_documents:
            frequencies: dict[str, int] = {}
            for token in document:
                frequencies[token] = frequencies.get(token, 0) + 1
            score = 0.0
            for term in terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                document_frequency = self._document_frequencies.get(term, 0)
                inverse_frequency = math.log(
                    1.0
                    + (self.size - document_frequency + 0.5)
                    / (document_frequency + 0.5)
                )
                denominator = frequency + k1 * (
                    1.0 - b + b * len(document) / average_length
                )
                score += inverse_frequency * frequency * (k1 + 1.0) / denominator
            scores.append(score)
        return scores

    @staticmethod
    def _term_coverage(terms: tuple[str, ...], document: tuple[str, ...]) -> float:
        query = set(terms)
        return len(query & set(document)) / len(query) if query else 0.0

    def save(self, index_path: Path, chunks_path: Path) -> None:
        """Persist the index and the chunk manifest (JSONL)."""
        index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(index_path))
        with chunks_path.open("w", encoding="utf-8") as fh:
            for chunk in self._chunks:
                fh.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")

    @classmethod
    def load(cls, index_path: Path, chunks_path: Path, min_score: float = 0.40) -> "FaissRetriever":
        """Load a saved index + chunk manifest."""
        if not index_path.exists():
            raise FileNotFoundError(
                f"FAISS index not found: {index_path}. Build it first "
                "(see README — index build step)."
            )
        if not chunks_path.exists():
            raise FileNotFoundError(f"Chunk manifest not found: {chunks_path}")

        index = faiss.read_index(str(index_path))
        retriever = cls(dimension=index.d, min_score=min_score)
        retriever._index = index
        with chunks_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                retriever._chunks.append(
                    Chunk(
                        chunk_id=record["chunk_id"],
                        doc_id=record["doc_id"],
                        page_number=int(record["page_number"]),
                        text=record["text"],
                        index=int(record["index"]),
                    )
                )
        retriever._chunk_positions = {
            chunk.chunk_id: position for position, chunk in enumerate(retriever._chunks)
        }
        retriever._lexical_documents = [
            _lexical_tokens(chunk.text) for chunk in retriever._chunks
        ]
        retriever._rebuild_lexical_statistics()
        if index.ntotal != len(retriever._chunks):
            raise ValueError(
                f"corrupt index/manifest: index has {index.ntotal} vectors "
                f"but manifest has {len(retriever._chunks)} chunks"
            )
        return retriever
