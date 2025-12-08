"""
Progress tracking and checkpointing utilities.

Purpose: Enable resumable pipeline runs with JSON-based progress tracking
Decision log:
  - JSON format for human-readability and easy debugging
  - Per-item status allows granular restart after failures
  - Automatic timestamping for audit trail
Date: 2024-12-08
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

Status = Literal["pending", "in_progress", "complete", "failed", "skipped"]


class ProgressTracker:
    """
    Track progress of batch operations with checkpoint/resume support.

    Usage:
        tracker = ProgressTracker(Path("data/interim/h3_pop_100m/_progress.json"))
        tracker.initialize(["tile_1", "tile_2", "tile_3"])

        for item_id in tracker.get_pending():
            tracker.mark_in_progress(item_id)
            try:
                process(item_id)
                tracker.mark_complete(item_id)
            except Exception as e:
                tracker.mark_failed(item_id, str(e))
    """

    def __init__(self, progress_file: Path):
        self.file = progress_file
        self.data = self._load()

    def _load(self) -> dict:
        """Load existing progress or create new."""
        if self.file.exists():
            return json.loads(self.file.read_text())
        return {
            "started_at": None,
            "updated_at": None,
            "status": "pending",
            "total_items": 0,
            "completed_items": 0,
            "failed_items": 0,
            "skipped_items": 0,
            "items": {},
        }

    def save(self) -> None:
        """Save progress to disk."""
        self.data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.file.parent.mkdir(parents=True, exist_ok=True)

        # Write atomically via temp file
        temp_file = self.file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(self.data, indent=2))
        temp_file.rename(self.file)

    def initialize(self, item_ids: list[str], reset: bool = False) -> None:
        """
        Initialize progress with list of items to process.

        Args:
            item_ids: List of item identifiers
            reset: If True, reset existing progress
        """
        if reset or not self.data["items"]:
            self.data["started_at"] = datetime.now(timezone.utc).isoformat()
            self.data["status"] = "in_progress"
            self.data["total_items"] = len(item_ids)
            self.data["items"] = {
                item_id: {"status": "pending"} for item_id in item_ids
            }
            self.save()
        else:
            # Add any new items not already tracked
            for item_id in item_ids:
                if item_id not in self.data["items"]:
                    self.data["items"][item_id] = {"status": "pending"}
            self.data["total_items"] = len(self.data["items"])
            self.save()

    def mark_in_progress(self, item_id: str) -> None:
        """Mark item as currently being processed."""
        self.data["items"][item_id] = {
            "status": "in_progress",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        self.save()

    def mark_complete(self, item_id: str, metadata: dict | None = None) -> None:
        """Mark item as successfully completed."""
        self.data["items"][item_id] = {
            "status": "complete",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }
        self._update_counts()
        self.save()

    def mark_failed(self, item_id: str, error: str) -> None:
        """Mark item as failed with error message."""
        self.data["items"][item_id] = {
            "status": "failed",
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "error": error,
        }
        self._update_counts()
        self.save()

    def mark_skipped(self, item_id: str, reason: str = "") -> None:
        """Mark item as skipped."""
        self.data["items"][item_id] = {
            "status": "skipped",
            "skipped_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
        }
        self._update_counts()
        self.save()

    def _update_counts(self) -> None:
        """Update summary counts."""
        statuses = [item["status"] for item in self.data["items"].values()]
        self.data["completed_items"] = statuses.count("complete")
        self.data["failed_items"] = statuses.count("failed")
        self.data["skipped_items"] = statuses.count("skipped")

        # Check if all done
        pending = statuses.count("pending") + statuses.count("in_progress")
        if pending == 0:
            self.data["status"] = "complete" if self.data["failed_items"] == 0 else "complete_with_errors"

    def get_pending(self) -> list[str]:
        """Get list of items not yet processed."""
        return [
            item_id
            for item_id, info in self.data["items"].items()
            if info["status"] in ("pending", "in_progress")
        ]

    def get_completed(self) -> list[str]:
        """Get list of successfully completed items."""
        return [
            item_id
            for item_id, info in self.data["items"].items()
            if info["status"] == "complete"
        ]

    def get_failed(self) -> list[str]:
        """Get list of failed items."""
        return [
            item_id
            for item_id, info in self.data["items"].items()
            if info["status"] == "failed"
        ]

    def is_complete(self, item_id: str) -> bool:
        """Check if specific item is complete."""
        return self.data["items"].get(item_id, {}).get("status") == "complete"

    def is_all_complete(self) -> bool:
        """Check if all items are complete."""
        return self.data["status"] in ("complete", "complete_with_errors")

    def get_summary(self) -> dict:
        """Get progress summary."""
        return {
            "status": self.data["status"],
            "total": self.data["total_items"],
            "completed": self.data["completed_items"],
            "failed": self.data["failed_items"],
            "skipped": self.data["skipped_items"],
            "pending": len(self.get_pending()),
        }

    def print_summary(self) -> None:
        """Print human-readable progress summary."""
        s = self.get_summary()
        print(f"Progress: {s['completed']}/{s['total']} complete")
        if s["failed"]:
            print(f"  Failed: {s['failed']}")
        if s["skipped"]:
            print(f"  Skipped: {s['skipped']}")
        if s["pending"]:
            print(f"  Pending: {s['pending']}")
