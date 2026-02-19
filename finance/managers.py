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
    def get_total_remaining(self):
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


