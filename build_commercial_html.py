# -*- coding: utf-8 -*-
"""Build the explicitly labelled demo site; no network access or email delivery."""

import argparse
import copy
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IDENTITY_FIELDS = ("county_id", "building_id", "name", "floor", "tax_id")
ICONS = (
    "apple-touch-icon.png", "favicon-16x16.png", "favicon-32x32.png",
    "favicon.ico", "favicon.svg", "icon-192.png", "icon-512.png",
)


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def company_id(company):
    identity = {key: company[key] for key in IDENTITY_FIELDS}
    digest = hashlib.sha256(canonical_json(identity).encode("utf-8")).hexdigest()
    return "demo_" + digest[:24]


def prepare_data(database, generated_at=None):
    """Remove fabricated identity/contact fields without mutating the source."""
    counties = copy.deepcopy(database["counties"])
    buildings = sorted(copy.deepcopy(database["buildings"]), key=lambda b: b["id"])
    by_county = {county_id: [] for county_id in counties}
    seen_ids = set()
    legacy_id_map = {}
    for original in database["companies"]:
        stable_id = company_id(original)
        if stable_id in seen_ids:
            raise ValueError(f"Duplicate company identity: {original['id']}")
        seen_ids.add(stable_id)
        if original["id"] in legacy_id_map:
            raise ValueError(f"Duplicate legacy company ID: {original['id']}")
        legacy_id_map[original["id"]] = stable_id
        company = dict(original)
        company.pop("low_voltage_needs", None)
        company.update(
            id=stable_id,
            legacy_id=original["id"],
            name="示範企業 " + stable_id[5:17].upper(),
            phone="",
            tax_id="",
            rep_name="",
            status="尚未拜訪",
            is_demo=True,
            source_verified_at=None,
        )
        by_county[company["county_id"]].append(company)

    building_counts = Counter(building["county_id"] for building in buildings)
    for building in buildings:
        building.update(is_demo=True, source_verified_at=None)
        building["company_count"] = sum(
            company["building_id"] == building["id"]
            for company in by_county[building["county_id"]]
        )
    for county_id, companies in by_county.items():
        companies.sort(key=lambda company: company["id"])
        counties[county_id]["company_count"] = len(companies)
        counties[county_id]["building_count"] = building_counts[county_id]

    catalog = {
        "schema_version": 1,
        "data_mode": "demo",
        "source_verified_at": None,
        "counties": counties,
        "categories": copy.deepcopy(database["categories"]),
        "buildings": buildings,
        "legacy_id_map": legacy_id_map,
    }
    version_content = {"catalog": catalog, "companies_by_county": by_county}
    catalog["dataset_version"] = hashlib.sha256(
        canonical_json(version_content).encode("utf-8")
    ).hexdigest()
    catalog["generated_at"] = generated_at or datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    ).replace("+00:00", "Z")
    return catalog, by_county


def write_data(directory, catalog, by_county):
    (directory / "counties").mkdir(parents=True, exist_ok=True)
    (directory / "catalog.json").write_text(canonical_json(catalog) + "\n", encoding="utf-8")
    for county_id, companies in by_county.items():
        (directory / "counties" / f"{county_id}.json").write_text(
            canonical_json({"companies": companies}) + "\n", encoding="utf-8"
        )


def build_site(root=ROOT, output=None):
    root = Path(root).resolve()
    output = Path(output).resolve() if output else root / "dist"
    if output == root:
        raise ValueError("Deployment output must be separate from the source directory")
    database = json.loads((root / "commercial_database_taiwan.json").read_text(encoding="utf-8"))
    catalog, by_county = prepare_data(database)
    html = (root / "src" / "index.html").read_text(encoding="utf-8")
    if "__DATABASE_BUNDLE_PLACEHOLDER__" in html or "const DB =" in html:
        raise ValueError("The HTML template must load data separately")

    # Keep the root preview and the Pages artifact on exactly the same dataset.
    (root / "index.html").write_text(html, encoding="utf-8")
    write_data(root / "data", catalog, by_county)
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_text(html, encoding="utf-8")
    write_data(output / "data", catalog, by_county)
    shutil.copytree(root / "assets", output / "assets", dirs_exist_ok=True)
    for icon in ICONS:
        shutil.copy2(root / icon, output / icon)
    (output / ".nojekyll").write_text("", encoding="utf-8")
    return catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist", help="Static Pages artifact directory")
    args = parser.parse_args()
    catalog = build_site(output=args.output)
    total = sum(county["company_count"] for county in catalog["counties"].values())
    print(f"Built {total} demo records across {len(catalog['counties'])} counties in {args.output}")
    print(f"Dataset version: {catalog['dataset_version']}")


if __name__ == "__main__":
    main()
