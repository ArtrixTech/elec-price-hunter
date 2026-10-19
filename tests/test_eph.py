"""Offline tests: parsers against recorded payloads, quantity pricing, number parsing.

  python3 -m unittest discover -s tests
"""
import json
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "elec-price-hunter", "scripts"))

from eph_sources import common, jlc, lceda, lcsc, mouser, pcbparts  # noqa: E402


def fixture(name):
    with open(os.path.join(HERE, "fixtures", name), encoding="utf-8") as f:
        return json.load(f)


class Numbers(unittest.TestCase):
    def test_num(self):
        self.assertEqual(common.num("$1,234.50"), 1234.5)
        self.assertEqual(common.num("7,50 €"), 7.5)
        self.assertEqual(common.num("2,648,712"), 2648712)
        self.assertEqual(common.num("1,234"), 1234)
        self.assertIsNone(common.num("-"))
        self.assertIsNone(common.num(None))

    def test_breaks_sorted_and_cleaned(self):
        self.assertEqual(common.breaks([(10, 0.5), (1, 0.8), (100, None), (5, 0)]),
                         [{"qty": 1, "price": 0.8}, {"qty": 10, "price": 0.5}])


class AtQty(unittest.TestCase):
    REC = {"price_breaks": [{"qty": 1, "price": 1.0}, {"qty": 10, "price": 0.8}, {"qty": 100, "price": 0.5}],
           "stock": 150, "currency": "CNY", "moq": None, "multiple": None}

    def test_tier_edges(self):
        self.assertEqual(common.at_qty(self.REC, 9)["unit"], 1.0)
        self.assertEqual(common.at_qty(self.REC, 10)["unit"], 0.8)
        self.assertEqual(common.at_qty(self.REC, 100)["total"], 50.0)

    def test_first_tier_is_minimum(self):
        r = dict(self.REC, price_breaks=[{"qty": 100, "price": 0.01}])
        q = common.at_qty(r, 20)
        self.assertEqual((q["buy"], q["total"]), (100, 1.0))

    def test_multiple_and_stock(self):
        q = common.at_qty(dict(self.REC, multiple=50), 120)
        self.assertEqual(q["buy"], 150)
        self.assertTrue(q["stock_ok"])
        self.assertFalse(common.at_qty(self.REC, 151)["stock_ok"])

    def test_no_price(self):
        self.assertIn("error", common.at_qty({"price_breaks": []}, 5))


class Lceda(unittest.TestCase):
    def test_part_exact_code(self):
        with mock.patch.object(lceda, "get_json", return_value=fixture("lceda_C8734.json")):
            r = lceda.part("c8734")
        self.assertEqual((r["sku"], r["mpn"], r["currency"]), ("C8734", "STM32F103C8T6", "CNY"))
        self.assertTrue(r["datasheet"].startswith("https://atta.szlcsc.com/"))
        self.assertTrue(r["url"].startswith("https://item.szlcsc.com/"))
        self.assertEqual(r["price_breaks"][0]["qty"], 1)
        self.assertEqual(r["pack_qty"], 250)

    def test_stock_in_pieces(self):
        d = fixture("lceda_C8734.json")
        p = next(x for x in d["result"]["productList"] if x["code"] == "C8734")
        p.update(stockNumber="4532", splitRatio="100")
        with mock.patch.object(lceda, "get_json", return_value=d):
            r = lceda.part("C8734")
        self.assertEqual((r["stock"], r["multiple"]), (453200, 100))

    def test_part_unknown(self):
        with mock.patch.object(lceda, "get_json", return_value={"result": {"productList": [], "total": 0}}):
            self.assertIsNone(lceda.part("C99999999"))

    def test_schema_change_raises(self):
        with mock.patch.object(lceda, "get_json", return_value={"result": None}):
            self.assertRaises(common.SchemaError, lceda.part, "C8734")
        with mock.patch.object(lceda, "get_json", return_value={"result": {"productList": [{"code": "C1"}]}}):
            self.assertRaises(common.SchemaError, lceda.search, "x")


class Lcsc(unittest.TestCase):
    def test_part(self):
        with mock.patch.object(lcsc, "get_json", return_value=fixture("lcsc_C8734.json")):
            r = lcsc.part("C8734")
        self.assertEqual((r["sku"], r["currency"]), ("C8734", "USD"))
        self.assertEqual(r["params"]["CPU Core"], "ARM Cortex-M3")
        self.assertIn("datasheet.lcsc.com", r["datasheet"])

    def test_unknown(self):
        with mock.patch.object(lcsc, "get_json", return_value={"code": 200, "result": None}):
            self.assertIsNone(lcsc.part("C99999999"))


class Jlc(unittest.TestCase):
    def test_price_string(self):
        with mock.patch.object(jlc, "get_json", return_value=fixture("jlc_C8734.json")):
            r = jlc.part("C8734")
        self.assertEqual(r["price_breaks"][0], {"qty": 1, "price": 1.4415})
        self.assertIn(r["jlc_class"], ("Basic", "Preferred", "Extended"))


class Mouser(unittest.TestCase):
    PART = {"MouserPartNumber": "511-X", "ManufacturerPartNumber": "X", "AvailabilityInStock": "2,648",
            "Min": "1", "Mult": "1", "IsDiscontinued": "true", "LifecycleStatus": None,
            "PriceBreaks": [{"Quantity": 10, "Price": "$0,08", "Currency": "USD"},
                            {"Quantity": 1, "Price": "$0.10", "Currency": "USD"}],
            "ProductAttributes": [{"AttributeName": "Packaging", "AttributeValue": "Reel"}]}

    def test_string_fields(self):
        r = mouser._rec(self.PART)
        self.assertEqual(r["stock"], 2648)
        self.assertEqual(r["lifecycle"], "Discontinued")
        self.assertEqual([b["qty"] for b in r["price_breaks"]], [1, 10])

    def test_fallback_without_key(self):
        res = {"results": [{"part_number": "511-X", "mfr_part_number": "X", "stock": 5,
                            "price_breaks": [{"qty": 1, "price": 7.5}], "currency": "USD"},
                           {"part_number": "511-XTR", "mfr_part_number": "XTR", "price_breaks": []}]}
        with mock.patch.dict(os.environ, {"MOUSER_SEARCH_API_KEY": ""}), \
                mock.patch.object(pcbparts, "call", return_value=res):
            recs = mouser.part("x")
        self.assertEqual([r["mpn"] for r in recs], ["X"])      # exact match only
        self.assertIn("pcbparts", recs[0]["note"])

    def test_search_needs_key(self):
        with mock.patch.dict(os.environ, {"MOUSER_SEARCH_API_KEY": ""}):
            self.assertRaises(common.NotConfigured, mouser.search, "x")


if __name__ == "__main__":
    unittest.main()
