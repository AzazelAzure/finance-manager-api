from django.contrib import admin
from .models import Category, Currency, Tag, UpcomingExpense, PaymentSource, Transaction, CurrentAsset, AppProfile
# Register your models here.
admin.site.register(Category)
admin.site.register(Currency)
admin.site.register(Tag)
admin.site.register(UpcomingExpense)
admin.site.register(PaymentSource)
admin.site.register(Transaction)
admin.site.register(CurrentAsset)
admin.site.register(AppProfile)