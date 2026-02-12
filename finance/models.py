# TODO: Migrate new tables once user requirement is done.  
# TODO: Create Docstrings

from django.db import models
from django.utils import timezone
from django.conf import settings
import uuid

class AppProfile(models.Model):
    
    username = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    last_login = models.DateField(null=True, blank=True)

    base_currency = models.ForeignKey(
        'finance.Currency', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    def __str__(self):
        return f'{self.user_id}'

class Category(models.Model):

    class Meta:
        verbose_name_plural= "Categories"
        ordering = ['name']

    # Sets the overarching category types
    class CatType(models.TextChoices):
        BILL = 'BILL', 'Recurring Bill'
        DAILY = 'DAILY', 'Daily Expense'
        INCOME = 'INCOME', 'Income Source'
        XFER = 'XFER', 'Transfer'

    # Ensure the category doesn't already exists.  
    name = models.CharField(max_length=50, unique=True)
    cat_type = models.CharField(max_length=10, choices=CatType.choices)

    # User dependancy
    uid = models.ForeignKey('user_id.AppProfile', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.get_cat_type_display()})"
    
class Currency(models.Model):

    class Meta:
        verbose_name_plural= "Currencies"
        ordering = ['code']

    code = models.CharField(max_length=3, unique=True, editable=False)
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=5, default='₱')

    # User dependancy
    uid = models.ForeignKey('user_id.AppProfile', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.code} ({self.symbol})'
    
class Tag(models.Model):
    name = models.CharField(max_length=200, unique=True)
    
    def __str__(self):
        return self.name
    
class PaymentSource(models.Model):

    class Meta:
        verbose_name_plural = "Payment Sources"
    
    class AccType(models.TextChoices):
        SAVINGS = 'SAVINGS', 'Savings'
        CHECKING = 'CHECKING', 'Checking'
        CASH = 'CASH', 'Cash'
        INVESTMENT = 'INVESTMENT', 'Investment'
        EWALLET= 'EWALLET', 'Mobile Wallet'

    source = models.CharField(max_length=50, unique=True)
    acc_type = models.CharField(max_length=10, choices=AccType.choices)

    # User dependancy
    uid = models.ForeignKey('user_id.AppProfile', on_delete=models.CASCADE)
    
    def __str__(self):
        return f'{self.source} ({self.AccType})'

class UpcomingExpense(models.Model):
    # The 'choices' class acts as our internal logic guard

    class Meta:
        ordering = ['due_date']

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'


    name = models.CharField(max_length=200, unique=True)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    paid_flag = models.BooleanField(default=False)

    # User dependancy
    uid = models.ForeignKey('user_id.AppProfile', on_delete=models.CASCADE)


    # This is the "State Machine" field
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )

    currency = models.ForeignKey('Currency', on_delete=models.PROTECT)

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

    class Meta:
        ordering = ['date']
    
    # Hard Coded Requirements
    date = models.DateField()
    description = models.CharField(max_length=200, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)


    # Link to relationship models
    category = models.ForeignKey('Category', on_delete=models.PROTECT)
    source = models.ForeignKey('PaymentSource', on_delete=models.PROTECT)
    currency = models.ForeignKey('Currency', on_delete=models.PROTECT)
    tags = models.ManyToManyField('Tag', blank=True)
    
    tx_id = models.CharField(max_length=20, unique=True, editable=False)

    # User dependancy
    uid = models.ForeignKey('user_id.AppProfile', on_delete=models.CASCADE)

    class TxType(models.TextChoices):
        EXPENSE = 'EXPENSE', 'Expense', 
        INCOME = 'INCOME', 'Income', 
        TRANSFER = 'XFER', 'Transfer', 
    
    tx_type = models.CharField(max_length=10, choices=TxType.choices)

    def save(self, *args, **kwargs):
        # Get and set a tx_id for unique transaction identifiers
        if not self.tx_id:
            day_suffix = timezone.now().year
            unique_id = str(uuid.uuid4())[:8].upper()
            self.tx_id = f"{day_suffix}-{unique_id}"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.tx_id
    
class CurrentAsset(models.Model):

    class Meta:
        verbose_name_plural = "Current Assets"
        
    source = models.ForeignKey('PaymentSource', on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.ForeignKey('code.Currency', on_delete=models.PROTECT)

    # User dependancy
    uid = models.ForeignKey('user_id.AppProfile', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.source.source} ({self.amount})'