import logic.implementors as implement
import logic.validators as validator
import logic.updaters as update
from django.db import transaction


@transaction.atomic
@validator.TransactionValidator
def user_add_transaction(data: dict):
    implement.add_transaction(**data)
    update.new_transaction(uid=data["uid"], is_income=data["is_income"])
    return


@transaction.atomic
@validator.TransferValidator
def user_add_transfer(data: list):
    xfer_out = data[0]
    xfer_in = data[1]
    implement.add_transaction(**xfer_out)
    update.new_transaction(uid=xfer_out["uid"], is_income=False)
    implement.add_transaction(**xfer_in)
    update.new_transaction(uid=xfer_in["uid"], is_income=True)
    return


@transaction.atomic
@validator.TransactionValidator
def user_add_bulk_transactions(data: list):
    for item in data:
        user_add_transaction(item)
    return


@transaction.atomic
def user_add_asset(data: dict):
    implement.add_asset(**data)
    update.rebalance(uid=data["uid"], acc_type=data["source"])
    return


@transaction.atomic
def user_change_asset(data):
    return
