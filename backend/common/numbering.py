from django.utils import timezone


def next_number(model, field, prefix, year=None):
    """Generate ``PREFIX-YYYY-####`` from the latest existing value.

    Callers wrap creation in a transaction; a unique constraint protects against
    rare concurrent collisions, and callers may retry.
    """

    year = year or timezone.now().year
    base = f'{prefix}-{year}-'
    last = (
        model.objects.filter(**{f'{field}__startswith': base})
        .order_by(f'-{field}')
        .values_list(field, flat=True)
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(str(last)[len(base):]) + 1
        except (TypeError, ValueError):
            seq = 1
    return f'{base}{seq:04d}'
