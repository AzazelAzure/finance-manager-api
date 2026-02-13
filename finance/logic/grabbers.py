# TODO: Add Docstrings
# TODO: Rename file

from finance.models import (
    CurrentAsset,
    Transaction,
    UpcomingExpense,
    AppProfile,
    Category,
    Currency,
    Tag,
    PaymentSource,
    FinancialSnapshot,
)
from django_utils import timezone


# Get Assets
def get_asset(uid, *args):
    return CurrentAsset.objects.filter(uid=uid, source__source__in=args)


def get_type(uid, *args):
    return CurrentAsset.objects.filter(uid=uid, source__acc_type__in=args)


def get_all_assets(uid):
    return CurrentAsset.objects.filter(uid=uid)


# Get transactions
def get_transactions(**kwargs):
    return Transaction.objects.filter(**kwargs)


def get_transactions_by_period(uid, start_date, end_date):
    return Transaction.objects.filter(uid=uid, date__range=[start_date, end_date])


def get_last_transaction(uid):
    return Transaction.objects.filter(uid=uid).order_by("entry_id").last()


# Get Expenses
def get_current_month(uid):
    current_month = timezone.now().month
    current_year = timezone.now().year
    remaining_bills = UpcomingExpense.objects.filter(
        uid=uid,
        paid_flag=False,
        status="ACTIVE",
        due_date__year=current_year,
        due_date__month=current_month,
    )
    return remaining_bills


def get_total_remaining(uid):
    remaining = UpcomingExpense.objects.filter(
        uid=uid, paid_flag=False, status="ACTIVE", due_date__lte=timezone.now().date()
    )
    return remaining


def get_expenses_by_period(uid, start_date, end_date):
    return UpcomingExpense.objects.filter(uid=uid, date__range=[start_date, end_date])


def get_expense(uid, name):
    return UpcomingExpense.objects.filter(uid=uid, name=name)


# Get Tags
def get_tags(uid):
    return Tag.objects.filter(uid=uid)


# Get Categories
def get_categories(uid):
    return Category.objects.filter(uid=uid)


def get_cat_by_type(uid, cat_type):
    return Category.objects.filter(uid=uid, cat_type=cat_type)


# Get Currencies
def get_currencies(uid):
    return Currency.objects.filter(uid=uid)


def get_currency_codes(uid):
    return Currency.objects.filter(uid=uid).values("code")


def get_currency_names(uid):
    return Currency.objects.filter(uid=uid).values("name")


# Get Payment Sources
def get_sources(uid):
    return PaymentSource.objects.filter(uid=uid).values("source")


def get_acc_types(uid):
    return PaymentSource.objects.filter(uid=uid).values("acc_type")


# Get User Info
def get_uid(username):
    profile = AppProfile.objects.filter(user__username=username)
    return profile.user_id


def get_base_currency(uid):
    return AppProfile.objects.get(uid=uid).get_base_currency


def get_spend_accounts(uid):
    return AppProfile.objects.filter(uid=uid).values_list("spend_accounts", flat=True)


# Get Snapshot Info
def get_total_assets(uid):
    return FinancialSnapshot.objects.get(uid=uid).total_assets


def get_safe_to_spend(uid):
    return FinancialSnapshot.objects.get(uid=uid).safe_to_spend


def get_total_savings(uid):
    return FinancialSnapshot.objects.get(uid=uid).total_savings


def get_total_checking(uid):
    return FinancialSnapshot.objects.get(uid=uid).total_checking


def get_total_investment(uid):
    return FinancialSnapshot.objects.get(uid=uid).total_investment


def get_total_cash(uid):
    return FinancialSnapshot.objects.get(uid=uid).total_cash


def get_total_ewallet(uid):
    return FinancialSnapshot.objects.get(uid=uid).total_ewallet


def get_total_monthly_spending(uid):
    return FinancialSnapshot.objects.get(uid=uid).total_monthly_spending


def get_total_remaining_expenses(uid):
    return FinancialSnapshot.objects.get(uid=uid).total_remaining_expenses


def get_full_snapshot(uid):
    return FinancialSnapshot.objects.filter(uid=uid)
