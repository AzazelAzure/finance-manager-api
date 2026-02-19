from django.db import models
from django.utils import timezone

class TransactionManager(models.QuerySet):
    def for_user(self, uid):
        return self.filter(uid=uid)
    def get_latest(self,uid):
        return self.filter(uid=uid).order_by("entry_id").last()
    def get_by_period(self, start_date, end_date):
        return self.filter(date__range=[start_date, end_date])
    def get_current_month(self):
        today = timezone.now().date()
        first_of_month = today.replace(day=1)
        return self.filter(date__range=[first_of_month, today])
    def get_tx_id(self, entry_id):
        return self.get(entry_id=entry_id).tx_id
    def get_by_tx_type(self, tx_type):
        return self.filter(tx_type=tx_type).all()
    def get_tx(self, tx_id):
        return self.get(tx_id=tx_id)
    def get_by_tag_name(self, tag_name):
        return self.filter(tags__name=tag_name)
    def get_by_category(self, cat_name):
        return self.filter(category__name=cat_name)
    def get_by_source(self, source):
        return self.filter(source__source=source)
    def get_by_currency(self, code):
        return self.filter(currency__code=code)
    def get_by_month(self, month, year):
        return self.filter(date__month=month, date__year=year)
    def get_by_year(self, year):
        return self.filter(date__year=year)
    
class CurrentAssetManager(models.QuerySet):
    def for_user(self, uid):
        return self.filter(uid=uid)
    def get_by_type(self, *args):
        return self.filter(source__acc_type__in=args)
    def get_asset(self, *args):
        return self.get(source__source__in=args)

class UpcomingExpenseManager(models.QuerySet):
    def for_user(self, uid):
        return self.filter(uid=uid)
    def get_current_month(self):
        today = timezone.now().date()
        first_of_month = today.replace(day=1)
        return self.filter(due_date__range=[first_of_month, today])
    def get_by_remaining(self):
        return self.filter(
            paid_flag=False, 
            status="ACTIVE",
            due_date__lte=timezone.now().date()
        )
    def get_expenses_by_period(self, start_date, end_date):
        return self.filter(date__range=[start_date, end_date])
    def get_expense(self, name):
        return self.filter(name=name)
    def get_expense_by_id(self, expense_id):
        return self.filter(expense_id=expense_id)
    def get_by_status(self, status):
        return self.filter(status=status)
    def get_expenseid(self, name):
        return self.get(name=name).expense_id
    def get_by_paid_flag(self, paid_flag):
        return self.filter(paid_flag=paid_flag)
    def get_by_recurring(self, recurring):
        return self.filter(is_recurring=recurring)

class TagManager(models.QuerySet):
    def for_user(self, uid):
        return self.filter(uid=uid)

class CategoryManager(models.QuerySet):
    def for_user(self, uid):
        return self.filter(uid=uid)
    def get_by_type(self, cat_type):
        return self.filter(cat_type=cat_type)
    def get_by_name(self, name):
        return self.filter(name=name)

class PaymentSourceManager(models.QuerySet):
    def for_user(self, uid):
        return self.filter(uid=uid)
    def get_by_type(self, acc_type):
        return self.filter(acc_type=acc_type)
    def get_by_source(self, source):
        return self.filter(source=source)
    
class AppProfileManager(models.QuerySet):
    def for_user(self, uid):
        return self.filter(user_id=uid)    
    def get_base_currency(self):
        return self.get().base_currency
    def get_spend_accounts(self, uid):
        return self.filter(user_id=uid).values_list("spend_accounts__acc_type", flat=True)
    
    
class FinancialSnapshotManager(models.QuerySet):
    def for_user(self, uid):
        return self.filter(uid=uid)
    def get_totals(self, acc_type):
        field_name = f"total_{acc_type.lower()}"
        return self.values_list(field_name, flat=True).first()
    def set_totals(self, acc_type, total):
        field_name = f"total_{acc_type.lower()}"
        self.update(**{field_name: total})


