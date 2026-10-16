from dataclasses import dataclass, field

from billing.tax import apply_tax


@dataclass
class Invoice:
    customer: str
    lines: list = field(default_factory=list)

    @property
    def subtotal(self):
        return sum(qty * price for qty, price in self.lines)

    @property
    def total(self):
        return apply_tax(self.subtotal)


def build_invoice(customer, lines):
    return Invoice(customer=customer, lines=list(lines))
