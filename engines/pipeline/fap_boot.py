"""
fap_boot.py — Bootstrap script for Folder Automations & Pipelines.

Run this to:
  1. Initialize Postgres schema
  2. Register the Paper Mill pipeline with all stations
  3. Create hot folder directories
  4. Start the FAP engine (or integrate into BIL service)

Usage:
  python fap_boot.py              # standalone
  python fap_boot.py --init-db    # just create schema
  python fap_boot.py --dry-run    # show what would happen

Integration with BIL:
  from engines.pipeline.fap_boot import create_engine
  engine = create_engine()
  engine.start()  # in a thread alongside BIL
"""

import argparse
import sys
import os
import logging
from pathlib import Path

# Add BIL root to path
BIL_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BIL_ROOT))

from engines.pipeline.pipeline_engine import PipelineEngine
from engines.pipeline.stations.classifier import ClassifierStation
from engines.pipeline.stations.media_transformer import MediaTransformStation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("FAP-Boot")

# ══════════════════════════════════════════════════════════════════
# FAP DIRECTORY STRUCTURE
# ══════════════════════════════════════════════════════════════════
FAP_ROOT = r"D:\FAP"
DIRS = {
    "intake":       os.path.join(FAP_ROOT, "intake"),
    "classified":   os.path.join(FAP_ROOT, "classified"),
    "media_routed":  os.path.join(FAP_ROOT, "media-routed"),
    "lossless":     os.path.join(FAP_ROOT, "lossless"),
    "vectorized":   os.path.join(FAP_ROOT, "vectorized"),
    "graded":       os.path.join(FAP_ROOT, "graded"),
    "axiom_mapped": os.path.join(FAP_ROOT, "axiom-mapped"),
    "output":       os.path.join(FAP_ROOT, "output"),
    "review":       os.path.join(FAP_ROOT, "_review"),
    "rejected":     os.path.join(FAP_ROOT, "_rejected"),
    "wiki":         os.path.join(FAP_ROOT, "wiki"),
    "queue":        os.path.join(FAP_ROOT, "_queue"),
    "logs":         os.path.join(FAP_ROOT, "logs"),
}

PG_DSN = "host=192.168.1.97 dbname=theophysics user=postgres"


def create_directories():
    for name, path in DIRS.items():
        os.makedirs(path, exist_ok=True)
        logger.info(f"  Dir: {path}")
    # Sub-review folders per station
    for station in ["classifier", "media-transform-router", "lossless", "vectorizer", "grader", "axiom-mapper"]:
        os.makedirs(os.path.join(DIRS["review"], station), exist_ok=True)
        os.makedirs(os.path.join(DIRS["rejected"], station), exist_ok=True)


def create_engine(pg_dsn: str = None) -> PipelineEngine:
    """Create and configure the FAP engine with Paper Mill pipeline."""
    engine = PipelineEngine(pg_dsn=pg_dsn or PG_DSN)

    # Station 1: Classifier
    classifier = ClassifierStation(
        input_dir=DIRS["intake"],
        output_dir=DIRS["classified"],
        review_dir=os.path.join(DIRS["review"], "classifier"),
        fail_dir=os.path.join(DIRS["rejected"], "classifier"),
        threshold_pass=0.6,
        threshold_fail=0.25,
    )
    engine.register_station(classifier, pipeline_name="paper-mill", order=1)

    # Station 2: media/text route decision.
    media_router = MediaTransformStation(
        input_dir=DIRS["classified"],
        output_dir=DIRS["media_routed"],
        lane_root=DIRS["media_routed"],
        review_dir=os.path.join(DIRS["review"], "media-transform-router"),
        fail_dir=os.path.join(DIRS["rejected"], "media-transform-router"),
        threshold_pass=0.55,
        threshold_fail=0.25,
    )
    engine.register_station(media_router, pipeline_name="paper-mill", order=2)

    # Stations 3-7 are next: lossless, vectorizer, grader, axiom rigor,
    # and portal/final package. They should be full StationBase subclasses.

    # Signal handler: log to console + could push to comms
    def on_signal(sig):
        prefix = {
            "gap": "🔴 GAP",
            "duplicate": "🟡 DUPLICATE",
            "quality": "🟠 QUALITY",
            "ready": "🟢 READY",
            "error": "❌ ERROR",
        }.get(sig.signal_type.value, "📡 SIGNAL")
        logger.info(f"{prefix}: {sig.message}")

    engine.on_signal(on_signal)

    return engine


def main():
    parser = argparse.ArgumentParser(description="FAP Bootstrap")
    parser.add_argument("--init-db", action="store_true",
                        help="Initialize Postgres schema only")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be created")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("FAP — Folder Automations & Pipelines")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("DRY RUN — showing planned structure:")
        for name, path in DIRS.items():
            exists = "✓" if os.path.exists(path) else "✗"
            logger.info(f"  [{exists}] {name}: {path}")
        return

    logger.info("Creating directory structure...")
    create_directories()

    engine = create_engine()

    if args.init_db:
        logger.info("Initializing Postgres schema...")
        engine.init_db()
        logger.info("Done. Schema created.")
        return

    # Initialize DB + start
    engine.init_db()
    logger.info("Starting FAP engine...")
    engine.start()

    try:
        logger.info("FAP running. Press Ctrl+C to stop.")
        import time
        while True:
            time.sleep(60)
            # Periodic sweep of cold folders
            engine.sweep()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        engine.stop()


if __name__ == "__main__":
    main()
