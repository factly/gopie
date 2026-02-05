from __future__ import annotations

import base64
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from PIL import Image


def _now_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


@dataclass
class VizIOManager:
    """Centralized I/O and path utilities for visualization tests.

    This class consolidates all filesystem and path concerns used by:
    - dataset generation and image rendering
    - test case generation (CSV/JSON output)
    - test case runner (loading inputs, saving results, generated images)
    """

    base_output_dir: Path

    def __init__(self, base_output_dir: str | Path):
        self.base_output_dir = Path(base_output_dir)

    # ---- Common paths ----
    @property
    def images_dir(self) -> Path:
        return self.base_output_dir / "images"

    @property
    def datasets_dir(self) -> Path:
        return self.base_output_dir / "datasets"

    @property
    def generated_images_dir(self) -> Path:
        return self.base_output_dir / "generated_images"

    # ---- Directory management ----
    def ensure_all_dirs(self) -> None:
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.generated_images_dir.mkdir(parents=True, exist_ok=True)

    def clean_images_and_datasets(self) -> None:
        if self.images_dir.exists() and self.images_dir.is_dir():
            shutil.rmtree(self.images_dir, ignore_errors=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def clear_generated_images_dir(self) -> None:
        if self.generated_images_dir.exists() and self.generated_images_dir.is_dir():
            shutil.rmtree(self.generated_images_dir, ignore_errors=True)
        self.generated_images_dir.mkdir(parents=True, exist_ok=True)

    # ---- Filenames for artifacts ----
    def build_viz_json_path(self, timestamp: Optional[str] = None) -> Path:
        ts = timestamp or _now_timestamp()
        return self.base_output_dir / f"viz_test_cases_{ts}.json"

    # CSV output is no longer supported.

    def results_path_for(self, input_json: Path) -> Path:
        return input_json.with_name(input_json.stem + "_results.jsonl")

    def results_json_path_for(self, input_json: Path) -> Path:
        return input_json.with_name(input_json.stem + "_results.json")

    def delete_existing_viz_cases_files(self) -> int:
        deleted = 0
        for pattern in ("viz_test_cases_*.json", "viz_test_cases_*.csv"):
            for f in self.base_output_dir.glob(pattern):
                try:
                    f.unlink(missing_ok=True)  # type: ignore[arg-type]
                    deleted += 1
                except Exception:
                    pass
        return deleted

    def delete_existing_results_files(self) -> int:
        deleted = 0
        for pattern in ("*_results.json", "*_results.jsonl"):
            for f in self.base_output_dir.glob(pattern):
                try:
                    f.unlink(missing_ok=True)  # type: ignore[arg-type]
                    deleted += 1
                except Exception:
                    pass
        return deleted

    # ---- File load/save helpers ----
    @staticmethod
    def load_json(path: Path) -> Any:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def save_json(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def append_jsonl(path: Path, item: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False))
            f.write("\n")

    # ---- Discovery helpers ----
    def find_latest_viz_json(self) -> Optional[Path]:
        files = list(self.base_output_dir.glob("viz_test_cases_*.json"))
        if not files:
            return None
        return max(files, key=lambda p: p.stat().st_mtime)

    # ---- Image helpers ----
    @staticmethod
    def resolve_path(path_str: str) -> Path:
        p = Path(path_str)
        return p if p.is_absolute() else Path.cwd() / p

    @staticmethod
    def open_image(path: Path) -> Optional[Image.Image]:
        try:
            return Image.open(path).convert("RGB")
        except Exception:
            return None

    @staticmethod
    def data_url_for_image_path(image_path: str) -> str:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    # ---- Altair chart output ----
    def save_chart_image(self, chart: Any, subdir: str = "images", prefix: str = "chart") -> str:
        if subdir == "generated_images":
            out_dir = self.generated_images_dir
        elif subdir == "images":
            out_dir = self.images_dir
        else:
            out_dir = self.base_output_dir / subdir

        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"{prefix}_{ts}.png"
        chart.save(str(path))
        return str(path)

    # ---- Dataset CSV output ----
    def save_dataset_csv(self, dataframe: Any, dataset_name: str) -> Optional[str]:
        try:
            # Dataset CSV output is intentionally disabled for visualization
            # artifacts. Datasets are expected to be stored externally (e.g. in
            # S3 or a project-level dataset store) so we avoid creating a
            # `datasets/` directory under the visualization output.
            return None
        except Exception:
            return None

    # ---- S3 JSON helper ----
    @staticmethod
    def get_json_from_s3_url(
        url: str,
        *,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str,
    ) -> Any:
        from urllib.parse import unquote, urlparse

        import boto3

        parsed = urlparse(url)
        key = unquote(parsed.path.lstrip("/"))
        if key.startswith(bucket + "/"):
            key = key[len(bucket) + 1 :]

        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        response = s3.get_object(Bucket=bucket, Key=key)
        return json.loads(response["Body"].read().decode("utf-8"))
