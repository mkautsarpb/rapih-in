VAT_RATE = 0.11


def apply_tax(amount):
    return round(amount * (1 + VAT_RATE), 2)
