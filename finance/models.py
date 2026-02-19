# TODO: Create Docstrings

from django.db import models
from django.utils import timezone
from django.conf import settings
from finance.management.managers import *
import uuid


class AppProfile(models.Model):
    objects = AppProfileManager.as_manager()
    username = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    last_login = models.DateField(null=True, blank=True)
    spend_accounts = models.ManyToManyField("PaymentSource", blank=True)
    base_currency = models.ForeignKey(
        "finance.Currency",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.user_id}"


class Category(models.Model):
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=['name', 'uid'], name='unique_category_per_user')
        ]
    objects = CategoryManager.as_manager()
    # Sets the overarching category types
    class CatType(models.TextChoices):
        BILL = "BILL", "Recurring Bill"
        DAILY = "DAILY", "Daily Expense"
        INCOME = "INCOME", "Income Source"
        XFER = "XFER", "Transfer"

    # Ensure the category doesn't already exists.
    name = models.CharField(max_length=50)
    cat_type = models.CharField(max_length=10, choices=CatType.choices)



    # User dependancy
    uid = models.ForeignKey("AppProfile", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.get_cat_type_display()})"


class Currency(models.Model):
    class Meta:
        verbose_name_plural = "Currencies"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=['code', 'name', 'symbol'],
                name='unique_currency_per_code'
            )
        ]
    code = models.CharField(max_length=3, default="USD")
    name = models.CharField(max_length=50, default="USD")
    symbol = models.CharField(max_length=5, default="$", null=True, blank=True)

    def __str__(self):
        return f"{self.code} ({self.symbol})"


class Tag(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name', 'uid'], name='unique_tag_per_user')
        ]
    name = models.CharField(max_length=200, )
    uid = models.ForeignKey("AppProfile", on_delete=models.CASCADE)
    objects = TagManager()
    def __str__(self):
        return self.name


class PaymentSource(models.Model):
    objects = PaymentSourceManager.as_manager()
    class Meta:
        verbose_name_plural = "Payment Sources"
        constraints = [
            models.UniqueConstraint(fields=['source', 'uid'], name='unique_source_per_user')
        ]

    class AccType(models.TextChoices):
        SAVINGS = "SAVINGS", "Savings"
        CHECKING = "CHECKING", "Checking"
        CASH = "CASH", "Cash"
        INVESTMENT = "INVESTMENT", "Investment"
        EWALLET = "EWALLET", "Mobile Wallet"

    source = models.CharField(max_length=50)
    acc_type = models.CharField(max_length=10, choices=AccType.choices)

    # User dependancy
    uid = models.ForeignKey("AppProfile", on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        """
        Automatically create a CurrentAsset when a PaymentSource is created.
        This ensures every PaymentSource has a corresponding asset tracking its balance.
        """
        created = self.pk is None
        super().save(*args, **kwargs)
        
        if created:
            # Get the user's base currency (should always exist)
            base_currency = self.uid.base_currency
            if not base_currency:
                # Fallback: get first currency for user if base_currency not set
                base_currency = Currency.objects.filter(uid=self.uid).first()
            
            if base_currency:
                # Create CurrentAsset with initial amount of 0
                # User can update the amount later via user_add_asset or transactions
                CurrentAsset.objects.get_or_create(
                    source=self,
                    defaults={
                        'amount': 0,
                        'currency': base_currency,
                        'uid': self.uid
                    }
                )

    def __str__(self):
        return f"{self.source} ({self.AccType})"


class UpcomingExpense(models.Model):
    # The 'choices' class acts as our internal logic guard
    objects = UpcomingExpenseManager.as_manager()

    class Meta:
        ordering = ["due_date"]
        constraints = [
            models.UniqueConstraint(fields=['name', 'uid'], name='unique_upcoming_expense_per_user')
        ]

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    name = models.CharField(max_length=200)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    paid_flag = models.BooleanField(default=False)
    expense_id = models.AutoField(primary_key=True)
    # User dependancy
    uid = models.ForeignKey("AppProfile", on_delete=models.CASCADE)

    # This is the "State Machine" field
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )

    currency = models.ForeignKey("Currency", on_delete=models.PROTECT)

    # Boolean for recurring logic
    is_recurring = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.status}) ({self.paid_flag})"

    def save(self, *args, **kwargs):
        """
        Check if the current date has surpassed the end_date.
        If so, we flip recurring to False so it doesn't spawn next month.
        """
        if self.end_date and timezone.now().date() > self.end_date:
            self.is_recurring = False
        super().save(*args, **kwargs)


class Transaction(models.Model):
    objects = TransactionManager.as_manager()

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=['tx_id', 'uid'], name='unique_transaction_per_user')
        ]
    # Hard Coded Requirements
    date = models.DateField()
    description = models.CharField(max_length=200, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Link to relationship models

    category = models.ForeignKey("Category", on_delete=models.PROTECT)
    source = models.ForeignKey("PaymentSource", on_delete=models.PROTECT)
    currency = models.ForeignKey("Currency", on_delete=models.PROTECT)
    tags = models.ManyToManyField("Tag", blank=True)
    entry_id = models.AutoField(primary_key=True, db_index=True)
    tx_id = models.CharField(max_length=20, editable=False)

    # User dependancy
    uid = models.ForeignKey("AppProfile", on_delete=models.CASCADE)

    class TxType(models.TextChoices):
        EXPENSE = (
            "EXPENSE",
            "Expense",
        )
        INCOME = (
            "INCOME",
            "Income",
        )
        TRANSFER_IN = (
            "XFER_IN",
            "Transfer In",
        )
        TRANSFER_OUT = (
            "XFER_OUT",
            "Transfer Out",
        )

    tx_type = models.CharField(max_length=10, choices=TxType.choices)

    def save(self, *args, **kwargs):
        # Get and set a tx_id for unique transaction identifiers
        if not self.tx_id:
            day_suffix = timezone.now().year
            unique_id = str(uuid.uuid4())[:8].upper()
            self.tx_id = f"{day_suffix}-{unique_id}"

        if not self.date:
            self.date = timezone.now().date()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.tx_id


class CurrentAsset(models.Model):
    objects = CurrentAssetManager.as_manager()

    class Meta:
        verbose_name_plural = "Current Assets"

    source = models.OneToOneField("PaymentSource", on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.ForeignKey("Currency", on_delete=models.PROTECT)

    # User dependancy
    uid = models.ForeignKey("AppProfile", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.source.source} ({self.amount})"


class FinancialSnapshot(models.Model):
    objects = FinancialSnapshotManager.as_manager()
    class Meta:
        verbose_name_plural = "Financial Snapshot"

    total_assets = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    safe_to_spend = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_savings = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_checking = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_investment = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_cash = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_ewallet = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_monthly_spending = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_remaining_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_leaks = models.DecimalField(max_digits=15, decimal_places=2, default=0)  
    uid = models.OneToOneField("AppProfile", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.total_assets}, {self.safe_to_spend}, {self.total_savings}, {self.total_checking}, {self.total_investment}, {self.total_cash}, {self.total_ewallet}, {self.total_monthly_spending}, {self.total_remaining_expenses}, {self.total_leaks}"
