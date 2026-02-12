# TODO: Add Docstrings
# TODO: Import and add logging

from finance.models import CurrentAsset, Transaction, UpcomingExpense, Currency, Tag, PaymentSource, Category, AppProfile

# Set Assets
def add_asset(**kwargs):
    data = kwargs
    CurrentAsset.objects.create(**data)
    return

def update_asset(uid, source, **kwargs):
    asset_instance = CurrentAsset.objects.get(uid=uid, source=source)
    for key, value in kwargs.items():
        setattr(asset_instance, key, value)
    asset_instance.save()
    return

def delete_asset(uid, source):
    asset_instance = CurrentAsset.objects.get(uid=uid, source=source)
    asset_instance.delete()
    return

# Set Transactions
def add_transaction(**kwargs):
    data = kwargs
    Transaction.objects.create(**data)
    return

def update_transaction(uid, tx_id, **kwargs):
    tx_instance = Transaction.objects.get(uid=uid, tx_id = tx_id)
    for key, value in kwargs.items():
        setattr(tx_instance, key, value)
    tx_instance.save()
    return

def delete_transaction(uid, tx_id):
    tx_instance = Transaction.objects.get(uid=uid, tx_id=tx_id)
    tx_instance.delete()
    return

# Set Expenses
def add_expense(**kwargs):
    data = kwargs
    UpcomingExpense.objects.create(**data)
    return

def update_expense(uid, name, **kwargs):
    exp_instance = UpcomingExpense.objects.get(uid=uid, name=name)
    for key, value in kwargs.items():
        setattr(exp_instance, key, value)
    exp_instance.save()
    return

def delete_expense(uid, name):
    exp_instance = UpcomingExpense.objects.get(uid=uid, name=name)
    exp_instance.delete()
    return


# Set Tags
def add_tag(uid, name):
    Tag.objects.create(uid=uid, name=name)
    return

def update_tag(uid, name,new_name):
    tag_instance = Tag.objects.get(uid=uid, name=name)
    setattr(tag_instance, name, new_name)
    return

def delete_tag(uid, name):
    tag_instance = Tag.objects.get(uid=uid, name=name)
    tag_instance.delete()
    return

# Set Currencies
def add_currency(**kwargs):
    data = kwargs
    Currency.objects.create(**data)
    return

def update_currency(uid, code, **kwargs):
    cur_instance = Currency.objects.get(uid=uid, code=code)
    for key, value in kwargs.items():
        setattr(cur_instance, key, value)
    cur_instance.save()
    return

def delete_currency(uid, code):
    cur_instance = Currency.objects.get(uid=uid, code=code)
    cur_instance.delete()
    return

# Set Payment Sources
def add_payment_source(**kwargs):
    data = kwargs
    PaymentSource.objects.create(**data)
    return

def update_source(uid, src, **kwargs):
    src_instance = PaymentSource.objects.get(uid=uid, source=src)
    for key, value in kwargs.items():
        setattr(src_instance, key, value)
    src_instance.save()
    return

def delete_source(uid, src):
    src_instance = PaymentSource.objects.get(uid=uid, source=src)
    src_instance.delete()
    return
    
# Set Categories
def add_category(**kwargs):
    data = kwargs
    Category.objects.create(**data)
    return

def update_category(uid, name, **kwargs):
    cat_instance = Category.objects.get(uid=uid, name=name)
    for key, value in kwargs.items():
        setattr(cat_instance, key, value)
    cat_instance.save()
    return

def delete_category(uid, name):
    cat_instance = Category.objects.get(uid=uid, name=name)
    cat_instance.delete()
    return

# Add User
def add_user(username):
    AppProfile.objects.create(username=username)
    return

def set_user_currency(uid, currency):
    usr_instance = AppProfile.objects.get(uid=uid)
    setattr(usr_instance, usr_instance.base_currency, currency)
    return

def delete_user(uid):
    usr_instance=AppProfile.objects.get(uid=uid)
    usr_instance.delete()
    return

def user_login(uid, date):
    usr_instance = AppProfile.objects.get(uid=uid)
    setattr(usr_instance, usr_instance.last_login, date)
    return
    
