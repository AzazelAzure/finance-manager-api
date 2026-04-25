"""
This module handles all validation logic for the finance manager application.
Verifies that the data provided is valid, and cleans strings to proper formats.

Transaction decorators live in :mod:`finance.validators.tx_validators` and are re-exported
here for backward compatibility.
Source decorators live in :mod:`finance.validators.source_validators` and are re-exported
here for backward compatibility.

Attributes:
    TransactionValidator: (re-export from tx_validators)
    TransactionIDValidator: (re-export from tx_validators)
    TransactionTypeValidator: Decorator to validate a transaction type.
    UserValidator: Decorator to validate a user.
    AssetValidator: Decorator to validate an asset.
    BulkAssetValidator: Decorator to validate a list of assets.
    UpcomingExpenseValidator: Decorator to validate an upcoming expense.s
"""

from functools import wraps
from typing import Any

from rest_framework.exceptions import ValidationError

from finance.validators.expense_validators import (
    UpcomingExpenseGetValidator,
    UpcomingExpenseSetValidator,
    _validate_expense,
)
from finance.validators.category_validators import CategoryGetValidator, CategorySetValidator
from finance.validators.tag_validators import TagGetValidator, TagSetValidator
from finance.validators.validation_core import _validate_currency, _validate_timezone
from finance.validators.source_validators import SourceGetValidator, SourceSetValidator
from finance.validators.tx_validators import TransactionIDValidator, TransactionValidator
from finance.validators.user_validators import UserValidator