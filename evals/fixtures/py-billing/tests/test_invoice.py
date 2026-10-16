import unittest

from billing import build_invoice


class InvoiceTest(unittest.TestCase):
    def test_total_includes_vat(self):
        inv = build_invoice("ACME", [(2, 50.0)])
        self.assertEqual(inv.subtotal, 100.0)
        self.assertEqual(inv.total, 111.0)


if __name__ == "__main__":
    unittest.main()
