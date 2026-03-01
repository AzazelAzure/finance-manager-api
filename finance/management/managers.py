"""
This module defines all managers for the finance manager application.
"""
from django.db import models
from django.utils import timezone
from datetime import date
from dateutil.relativedelta import relativedelta

class TransactionManager(models.QuerySet):
    """Manager for Transaction model."""
    def for_user(self, uid):
        """Returns a queryset for a user."""
        return self.filter(uid=uid)
    
    def get_latest(self,uid):
        """Returns a model instance for the latest transaction for a user."""
        return self.filter(uid=uid).order_by("entry_id").last()
    
    def get_by_period(self, start_date, end_date):
        """Returns a queryset for transactions within a date range."""
        return self.filter(date__range=[start_date, end_date])
    
    def get_all_before(self, end_date):
        """Returns a queryset for transactions before a given date."""
        return self.filter(date__lte=end_date)
    
    def get_all_after(self, start_date):
        """Returns a queryset for transactions after a given date."""
        return self.filter(date__gte=start_date)
    
    def get_current_month(self):
        """Returns a queryset for transactions in the current month."""
        today = timezone.now().date()
        first_of_month = today.replace(day=1)
        return self.filter(date__range=[first_of_month, today])
    
    def get_last_month(self):
        """Returns a queryset for transactions in the last month."""
        today = timezone.now().date()
        today.replace(day=1)
        last_month_start = today - relativedelta(months=1)
        last_month_end = today - relativedelta(days=1)
        return self.filter(date__range=[last_month_start, last_month_end])
    
    def get_previous_week(self):
        """Returns a queryset for transactions in the previous week."""
        # TODO: Fix logic later to account for user defined start of week
        start_of_week = timezone.now().date() - relativedelta(weekday=6)
        end_of_week = start_of_week + relativedelta(days=7)
        return self.filter(date__range=[start_of_week, end_of_week])
    
    def get_by_tx_type(self, tx_type):
        """Returns a queryset for transactions of a given type."""
        return self.filter(tx_type=tx_type)
    
    def get_tx(self, tx_id):
        """Returns a queryset for a given transaction id."""
        return self.filter(tx_id=tx_id)
    
    def get_by_tag_name(self, tag_name):
        """Returns a queryset for transactions with a given tag name."""
        if not isinstance(tag_name, list):
            tag_name = [tag_name]
        return self.filter(tags__contains=tag_name)
    
    def get_by_category(self, cat_name):
        """Returns a queryset for transactions with a given category."""
        return self.filter(category__name=cat_name)
    
    def get_by_source(self, source):
        """Returns a queryset for transactions with a given source."""
        return self.filter(source__source=source)
    
    def get_by_currency(self, code):
        """Returns a queryset for transactions with a given currency."""
        return self.filter(currency__code=code)
    
    def get_by_date(self, date):
        """Returns a queryset for transactions with a given date."""
        return self.filter(date=date)
    
    def get_by_month(self, month, year):
        """Returns a queryset for transactions in a given month."""
        return self.filter(date__month=month, date__year=year)
    
    def get_by_year(self, year):
        """Returns a queryset for transactions in a given year."""
        return self.filter(date__year=year)

    def get_gte(self, amount):
        """Returns a queryset for transactions with an amount greater than or equal to a given amount."""
        return self.filter(amount__gte=amount)
    
    def get_lte(self, amount):
        """Returns a queryset for transactions with an amount less than or equal to a given amount."""
        return self.filter(amount__lte=amount)
    
class CurrentAssetManager(models.QuerySet):
    """Manager for CurrentAsset model."""
    def for_user(self, uid):
        """Returns a queryset for a user."""
        return self.filter(uid=uid)
    
    def get_by_type(self, *args):
        """Returns a queryset for assets of a given type."""
        return self.filter(source__acc_type__in=args)
    
    def get_asset(self, *args):
        """Returns a queryset for a given asset."""
        return self.filter(source__source__in=args)

class UpcomingExpenseManager(models.QuerySet):
    """Manager for UpcomingExpense model."""
    def for_user(self, uid):
        """Returns a queryset for a user."""
        return self.filter(uid=uid)
    
    def get_by_name(self, name):
        """Returns a queryset for a given expense name."""
        return self.filter(name=name)
    
    def get_by_due_date(self, due_date):
        """Returns a queryset for a given due date."""
        return self.filter(due_date=due_date)
    
    def get_by_end_date(self, end_date):
        """Returns a queryset for a given end date."""
        return self.filter(end_date=end_date)
    
    def get_by_start_date(self, start_date):
        """Returns a queryset for a given start date."""
        return self.filter(start_date=start_date)
    
    def get_by_currency(self, currency_code):
        """Returns a queryset for a given currency code."""
        return self.filter(currency__code=currency_code)
    
    def get_current_month(self):
        """Returns a queryset for upcoming expenses in the current month."""
        today = timezone.now().date()
        first_of_month = today.replace(day=1)
        return self.filter(due_date__range=[first_of_month, today])
    
    def get_by_remaining(self):
        """Returns a queryset for upcoming expenses with paid flag set to False."""
        return self.filter(paid_flag=False)
    
    def get_expenses_by_period(self, start_date, end_date):
        """Returns a queryset for upcoming expenses within a date range."""
        return self.filter(date__range=[start_date, end_date])
    
    def get_expenses_before(self, end):
        """Returns a queryset for upcoming expenses before a given date."""
        return self.filter(date__lte=end)
    
    def get_expenses_after(self, start):
        """Returns a queryset for upcoming expenses after a given date."""
        return self.filter(date__gte=start)
    
    def get_expense(self, name):
        """Returns a queryset for a given expense name."""
        return self.filter(name=name)
    
    def get_expense_by_id(self, expense_id):
        """Returns a queryset for a given expense id."""
        return self.filter(expense_id=expense_id)
    
    def get_expenseid(self, name):
        """Returns the expense id for a given expense name."""
        return self.get(name=name).expense_id
    
    def get_by_paid_flag(self, paid_flag):
        """Returns a queryset for upcoming expenses with a given paid flag."""
        return self.filter(paid_flag=paid_flag)
    
    def get_by_recurring(self, recurring):
        """Returns a queryset for upcoming expenses with a given recurring flag."""
        return self.filter(is_recurring=recurring)
    
    def get_all_upcoming(self):
        """Returns a queryset for all upcoming expenses."""
        return self.filter(due_date__lte=timezone.now().date())

class TagManager(models.QuerySet):
    """Manager for Tag model."""
    def for_user(self, uid):
        """Returns a queryset for a user."""
        return self.filter(uid=uid)
    
    def get_by_name(self, name):
        """Returns a queryset for a given tag name."""
        return self.filter(name=name)

class PaymentSourceManager(models.QuerySet):
    """Manager for PaymentSource model."""
    def for_user(self, uid):
        """Returns a queryset for a user."""
        return self.filter(uid=uid)
    
    def get_by_type(self, acc_type):
        """Returns a queryset for payment sources of a given type."""
        return self.filter(acc_type=acc_type)
    
    def get_by_source(self, source):
        """Returns a queryset for payment sources with a given source."""
        return self.filter(source=source)
    
class AppProfileManager(models.QuerySet):
    """Manager for AppProfile model."""
    def for_user(self, uid):
        """Returns a queryset for a user."""
        return self.filter(user_id=uid)    
    
    def get_base_currency(self):
        """Returns the base currency for a user."""
        return self.get().base_currency
    
    def get_spend_accounts(self):
        """Returns a tuple of spend accounts for a user."""
        return self.get().values_list("spend_accounts__source")
    
    def get_timezone(self):
        """Returns the timezone for a user."""
        return self.get().timezone

    def get_start_of_week(self):
        """Returns the start of week for a user."""
        return self.get().start_of_week
        
class FinancialSnapshotManager(models.QuerySet):
    """Manager for FinancialSnapshot model."""
    def for_user(self, uid):
        """Returns a queryset for a user."""
        return self.filter(uid=uid)
    
    def get_totals(self, acc_type):
        """Returns a list of all totals for a user."""
        field_name = f"total_{acc_type.lower()}"
        return self.values_list(field_name, flat=True).first()
    
    def set_totals(self, acc_type, total):
        """Sets the total for a given account type."""
        field_name = f"total_{acc_type.lower()}"
        self.update(**{field_name: total})

