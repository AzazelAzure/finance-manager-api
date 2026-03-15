import factory
from django.contrib.auth.models import User
from django.conf import settings
from finance.models import *
from factory import fuzzy, LazyAttribute
from faker import Faker
from decimal import Decimal

# Instantiate Faker once globally for factories
_faker = Faker()


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


class PaymentSourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PaymentSource

    uid = factory.Faker("uuid4")
    source = factory.Sequence(lambda n: f"source-{n}")
    acc_type = factory.Faker("random_element", elements=("SAVINGS", "CHECKING", "CASH", "INVESTMENT", "EWALLET", "UNKNOWN"))
    amount = LazyAttribute(
        lambda o: _faker.pydecimal(left_digits=5, right_digits=2).quantize(Decimal("0.01")))
    currency = fuzzy.FuzzyChoice(settings.SUPPORTED_CURRENCIES)



class TagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tag
    uid = factory.Faker("uuid4")
    tags = factory.Faker("word")

class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Transaction

    uid = factory.Faker("uuid4")
    date = factory.Faker("date")
    description = factory.Sequence(lambda n: f"tx-{n}")
    amount = LazyAttribute(
        lambda o: _faker.pydecimal(left_digits=5, right_digits=2).quantize(Decimal("0.01")))
    source = factory.Faker("word")
    currency = fuzzy.FuzzyChoice(settings.SUPPORTED_CURRENCIES)
    tx_type = factory.Faker("random_element", elements=("EXPENSE", "INCOME", "XFER_OUT", "XFER_IN"))
    bill = factory.Faker("word")


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    uid = factory.Faker("uuid4")
    name = factory.Sequence(lambda n: f"category-{n}")


class UpcomingExpenseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UpcomingExpense

    uid = factory.Faker("uuid4")
    name = factory.Sequence(lambda n: f"expense-{n}")
    estimated_cost = factory.Faker("random_int", min=100, max=1000)
    due_date = factory.Faker("date")
    start_date = factory.Faker("date")
    end_date = factory.Faker("date")
    paid_flag = factory.Faker("boolean")
    expense_id = factory.Faker("random_int", min=100, max=1000)
    status = factory.Faker("random_element", elements=("PENDING", "ACTIVE", "COMPLETED", "CANCELLED"))
    is_recurring = factory.Faker("boolean")
    currency = fuzzy.FuzzyChoice(settings.SUPPORTED_CURRENCIES)
