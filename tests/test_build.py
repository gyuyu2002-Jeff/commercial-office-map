import copy
import json
import tempfile
import unittest
from pathlib import Path

from build_commercial_html import ICONS, ROOT, build_site, company_id, prepare_data


def strings_in(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings_in(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings_in(child)


class DemoDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = json.loads((ROOT / "commercial_database_taiwan.json").read_text(encoding="utf-8"))
        cls.catalog, cls.counties = prepare_data(cls.original, "2026-11-06T00:00:00Z")
        cls.companies = [company for companies in cls.counties.values() for company in companies]

    def test_fabricated_identity_and_contact_information_are_not_published(self):
        output_strings = set(strings_in([self.catalog, list(self.counties.values())]))
        for source in self.original["companies"]:
            for field in ("name", "phone", "tax_id", "rep_name"):
                self.assertNotIn(source[field], output_strings)
        for company in self.companies:
            self.assertTrue(company["name"].startswith("示範企業 "))
            self.assertEqual((company["phone"], company["tax_id"], company["rep_name"]), ("", "", ""))
            self.assertTrue(company["is_demo"])
            self.assertIsNone(company["source_verified_at"])
        self.assertEqual(self.catalog["data_mode"], "demo")
        self.assertIsNone(self.catalog["source_verified_at"])
        self.assertTrue(all(building["is_demo"] for building in self.catalog["buildings"]))

    def test_no_prefilled_visit_progress(self):
        self.assertEqual({company["status"] for company in self.companies}, {"尚未拜訪"})
        self.assertEqual(len(self.companies), len(self.original["companies"]))

    def test_company_ids_and_dataset_version_survive_reordering_and_build_time(self):
        reordered = copy.deepcopy(self.original)
        reordered["companies"].reverse()
        reordered["buildings"].reverse()
        catalog, counties = prepare_data(reordered, "2026-12-01T00:00:00Z")
        self.assertEqual(catalog["legacy_id_map"], self.catalog["legacy_id_map"])
        self.assertEqual(counties, self.counties)
        self.assertEqual(catalog["dataset_version"], self.catalog["dataset_version"])
        self.assertNotEqual(catalog["generated_at"], self.catalog["generated_at"])
        source = dict(self.original["companies"][0])
        source["id"] = "C_renumbered"
        self.assertEqual(company_id(source), company_id(self.original["companies"][0]))

    def test_duplicate_identity_is_rejected_instead_of_merging_visit_records(self):
        duplicate = copy.deepcopy(self.original)
        duplicate["companies"].append(dict(duplicate["companies"][0], id="C_duplicate"))
        with self.assertRaisesRegex(ValueError, "Duplicate company identity"):
            prepare_data(duplicate)

    def test_all_ids_unique_and_legacy_mapping_is_complete(self):
        ids = [company["id"] for company in self.companies]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(set(ids), set(self.catalog["legacy_id_map"].values()))
        self.assertEqual(set(self.catalog["legacy_id_map"]), {c["id"] for c in self.original["companies"]})
        for company in self.companies:
            self.assertEqual(self.catalog["legacy_id_map"][company["legacy_id"]], company["id"])

    def test_county_and_building_counts_match_exported_records(self):
        for county_id, county in self.catalog["counties"].items():
            self.assertEqual(county["company_count"], len(self.counties[county_id]))
            self.assertTrue(all(c["county_id"] == county_id for c in self.counties[county_id]))
            self.assertEqual(county["building_count"], sum(b["county_id"] == county_id for b in self.catalog["buildings"]))
        for building in self.catalog["buildings"]:
            self.assertEqual(building["company_count"], sum(c["building_id"] == building["id"] for c in self.counties[building["county_id"]]))
        self.assertEqual(len(self.catalog["buildings"]), 154)
        self.assertEqual(len(self.catalog["counties"]), 22)

    def test_prepare_data_preserves_original_source(self):
        before = copy.deepcopy(self.original)
        prepare_data(self.original)
        self.assertEqual(self.original, before)

    def test_site_artifact_contains_only_site_assets_and_separate_demo_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "commercial_database_taiwan.json").write_text(json.dumps(self.original), encoding="utf-8")
            (root / "src").mkdir()
            template = (ROOT / "src" / "index.html").read_text(encoding="utf-8")
            (root / "src" / "index.html").write_text(template, encoding="utf-8")
            (root / "assets").mkdir()
            (root / "assets" / "app.js").write_text("// app fixture", encoding="utf-8")
            for icon in ICONS:
                (root / icon).write_bytes(b"icon fixture")
            build_site(root)
            dist = root / "dist"
            self.assertEqual((dist / "index.html").read_text(encoding="utf-8"), template)
            self.assertEqual((root / "index.html").read_text(encoding="utf-8"), template)
            self.assertNotIn("const DB =", template)
            self.assertNotIn("__DATABASE_BUNDLE_PLACEHOLDER__", template)
            self.assertNotIn(self.original["companies"][0]["phone"], template)
            self.assertFalse((dist / "commercial_database_taiwan.json").exists())
            self.assertTrue((dist / "assets" / "app.js").is_file())
            self.assertTrue((dist / ".nojekyll").is_file())
            self.assertEqual((root / "data" / "catalog.json").read_bytes(), (dist / "data" / "catalog.json").read_bytes())
            for county_id in self.original["counties"]:
                relative = Path("data") / "counties" / f"{county_id}.json"
                self.assertEqual((root / relative).read_bytes(), (dist / relative).read_bytes())
                self.assertEqual(json.loads((dist / relative).read_text(encoding="utf-8"))["companies"], self.counties[county_id])


if __name__ == "__main__":
    unittest.main()