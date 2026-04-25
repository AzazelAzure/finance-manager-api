from django.contrib import admin
from .models import Tag, UpcomingExpense, PaymentSource, Transaction, Category, AppProfile
# Register your models here.

admin.site.register(Tag)
admin.site.register(UpcomingExpense)
admin.site.register(PaymentSource)
admin.site.register(Transaction)
admin.site.register(AppProfile)
admin.site.register(Category)