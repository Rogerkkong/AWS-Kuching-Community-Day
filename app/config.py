"""Central configuration: environment variables, paths and tunable thresholds."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from platformdirs import user_data_dir

try:  # .env is optional
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


def _repo_root() -> Path:
    # PyInstaller one-folder build: resources live next to the executable (sys._MEIPASS for bundled data).
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


REPO_ROOT = _repo_root()
BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", REPO_ROOT))

if load_dotenv is not None:
    load_dotenv(REPO_ROOT / ".env", override=False)

APP_NAME = "PekelilingNavigator"
APP_TITLE = "MixUp Navigator"

TIERS = {0: "terbuka", 1: "terhad", 2: "sulit"}
TIER_LABELS = {0: "TERBUKA", 1: "TERHAD", 2: "SULIT"}

DEFAULT_STATUSES = ("IN_FORCE", "AMENDED", "UNKNOWN", "RECORD")
HISTORICAL_STATUSES = ("CANCELLED", "ONE_OFF")
RULE_DOC_TYPES = ("circular", "policy", "sop", "guideline")
RECORD_DOC_TYPES = ("minutes", "report")

REFUSAL_MESSAGE = (
    "Maaf, saya tidak menemui jawapan dalam pekeliling yang berkuat kuasa. / "
    "Sorry, I couldn't find this in the circulars currently in force."
)


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _path_env(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser().resolve() if value else default


@dataclass
class Settings:
    inference_backend: str = field(default_factory=lambda: _env("INFERENCE_BACKEND", "ollama"))
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", "qwen3:4b"))
    embed_model: str = field(default_factory=lambda: _env("EMBED_MODEL", "bge-m3"))
    embed_dim: int = 1024
    ollama_url: str = field(default_factory=lambda: _env("OLLAMA_URL", "http://127.0.0.1:11434"))
    ollama_keep_alive: str = field(default_factory=lambda: _env("OLLAMA_KEEP_ALIVE", "30m"))
    reranker: str = field(default_factory=lambda: _env("RERANKER", "auto"))
    rerank_model: str = field(default_factory=lambda: _env("RERANK_MODEL", "BAAI/bge-reranker-v2-m3"))
    llamacpp_server: str = field(default_factory=lambda: _env("LLAMACPP_SERVER", "models/llama-server.exe"))
    llamacpp_chat_gguf: str = field(default_factory=lambda: _env("LLAMACPP_CHAT_GGUF", "models/qwen3-4b-q4_k_m.gguf"))
    llamacpp_embed_gguf: str = field(default_factory=lambda: _env("LLAMACPP_EMBED_GGUF", "models/bge-m3-q8_0.gguf"))
    llamacpp_rerank_gguf: str = field(default_factory=lambda: _env("LLAMACPP_RERANK_GGUF", "models/bge-reranker-v2-m3-q8_0.gguf"))
    query_rewrite_mode: str = field(default_factory=lambda: _env("QUERY_REWRITE_MODE", "llm"))
    query_rewrite_timeout: float = field(default_factory=lambda: float(_env("QUERY_REWRITE_TIMEOUT", "8")))
    temperature: float = 0.1
    answer_max_tokens: int = 600
    num_ctx: int = 4096

    # Retrieval
    rrf_k: int = 60
    vector_k: int = 100
    per_list_limit: int = 30
    rerank_candidates: int = 20
    context_passages: int = 5
    passage_words: int = 250
    excluded_top_n: int = 10

    # Confidence thresholds on the top reranker score, per reranker kind (tuned on the golden set).
    confidence_thresholds: dict = field(default_factory=lambda: {
        "crossencoder": {"high": 0.70, "medium": 0.35},
        "embedding": {"high": 0.62, "medium": 0.50},
        "fake": {"high": 0.30, "medium": 0.12},
        "none": {"high": 0.05, "medium": 0.03},
    })
    # Passages scoring below this floor are not shown or sent to the model (per reranker kind).
    min_source_score: dict = field(default_factory=lambda: {
        "crossencoder": 0.05, "embedding": 0.40, "fake": 0.06, "none": 0.0,
    })
    # A jurisdiction counts as "strong" (for the side-by-side panel) at or above the medium threshold,
    # and both jurisdictions' best rules must reach this share of the top score.
    conflict_ratio: float = 0.75

    # Paths
    repo_root: Path = REPO_ROOT
    data_dir: Path = field(default_factory=lambda: _path_env("PN_DATA_DIR", Path(user_data_dir(APP_NAME, False))))
    workspace_dir: Path = field(default_factory=lambda: _path_env("PN_WORKSPACE", REPO_ROOT / "workspace"))
    dist_packs_dir: Path = field(default_factory=lambda: _path_env("PN_DIST_PACKS", REPO_ROOT / "dist_packs"))
    raw_dir: Path = REPO_ROOT / "data" / "raw"
    ground_truth_dir: Path = field(default_factory=lambda: _path_env("PN_GROUND_TRUTH", BUNDLE_ROOT / "data"))
    ui_dist: Path = BUNDLE_ROOT / "ui" / "dist"
    public_key_path: Path = field(default_factory=lambda: _path_env(
        "PN_PUBLIC_KEY", BUNDLE_ROOT / "app" / "resources" / "publisher_public.pem"))

    @property
    def app_db(self) -> Path:
        return self.data_dir / "app.db"

    @property
    def packs_dir(self) -> Path:
        return self.data_dir / "packs"

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

    @property
    def publisher_db(self) -> Path:
        return self.workspace_dir / "publisher.db"

    @property
    def private_key_path(self) -> Path:
        return _path_env("PN_PRIVATE_KEY", self.workspace_dir / "keys" / "publisher_private.pem")

    @property
    def uploads_dir(self) -> Path:
        return self.workspace_dir / "uploads"

    @property
    def embedding_model_id(self) -> str:
        """Identifier written into packs; must match between Publisher and Officer (rule 8)."""
        if self.inference_backend == "fake":
            return "fake-hash-1024"
        return self.embed_model

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.packs_dir, self.exports_dir):
            d.mkdir(parents=True, exist_ok=True)


def today() -> date:
    value = os.environ.get("PN_TODAY")
    return date.fromisoformat(value) if value else date.today()


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> Settings:
    """Re-read the environment (used by tests)."""
    global _settings
    _settings = Settings()
    return _settings
