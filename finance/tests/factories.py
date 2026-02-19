import factory
from django.contrib.auth.models import User
from finance.models import *

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@test.com")
    password = factory.PostGenerationMethodCall("set_password", "testpassword")

class AppProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AppProfile 
    
    user = factory.SubFactory(UserFactory)

class CurrencyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Currency

    uid = factory.SubFactory(AppProfileFactory)
    code = factory.Faker("currency_code")
    name = factory.Faker("word")
    symbol = factory.Faker("currency_symbol")


class PaymentSourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PaymentSource

    uid = factory.SubFactory(AppProfileFactory)
    source = factory.Faker("word")
    acc_type = factory.Faker("random_element", elements=("SAVINGS", "CHECKING", "CASH", "INVESTMENT", "EWALLET"))

class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    uid = factory.SubFactory(AppProfileFactory)
    name = factory.Faker("word")
    cat_type = factory.Faker("random_element", elements=("BILL", "DAILY", "INCOME", "XFER"))

class TagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tag
    uid = factory.SubFactory(AppProfileFactory)
    name = factory.Faker("word")

class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Transaction

    uid = factory.SubFactory(AppProfileFactory)
    date = factory.Faker("date")
    description = factory.Faker("sentence")
    amount = factory.Faker("random_int", min=100, max=1000)
    category = factory.SubFactory(CategoryFactory, uid=factory.SelfAttribute('..uid'))
    source = factory.SubFactory(PaymentSourceFactory, uid=factory.SelfAttribute('..uid'))
    currency = factory.SubFactory(CurrencyFactory, uid=factory.SelfAttribute('..uid'))
    tx_type = factory.Faker("random_element", elements=("EXPENSE", "INCOME"))

class CurrentAssetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CurrentAsset

    uid = factory.SubFactory(AppProfileFactory)
    source = factory.SubFactory(PaymentSourceFactory, uid=factory.SelfAttribute('..uid'))
    amount = factory.Faker("random_int", min=100, max=1000)
    currency = factory.SubFactory(CurrencyFactory, uid=factory.SelfAttribute('..uid'))


class UpcomingExpenseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UpcomingExpense

    uid = factory.SubFactory(AppProfileFactory)
    name = factory.Faker("sentence")
    estimated_cost = factory.Faker("random_int", min=100, max=1000)
    due_date = factory.Faker("date")
    start_date = factory.Faker("date")
    end_date = factory.Faker("date")
    paid_flag = factory.Faker("boolean")
    expense_id = factory.Faker("random_int", min=100, max=1000)
    status = factory.Faker("random_element", elements=("PENDING", "ACTIVE", "COMPLETED", "CANCELLED"))
    is_recurring = factory.Faker("boolean")
    currency = factory.SubFactory(CurrencyFactory, uid=factory.SelfAttribute('..uid'))











