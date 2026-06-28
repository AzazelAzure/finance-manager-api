from django.contrib import admin
from .models import (
    Tag,
    UpcomingExpense,
    PaymentSource,
    Transaction,
    Category,
    AppProfile,
    BalanceSnapshot,
    DailyUsageSnapshot,
    InviteChainEvent,
    SupportTicket,
)
# Register your models here.

admin.site.register(Tag)
admin.site.register(UpcomingExpense)
admin.site.register(PaymentSource)
admin.site.register(Transaction)
admin.site.register(AppProfile)
admin.site.register(Category)
admin.site.register(SupportTicket)
admin.site.register(DailyUsageSnapshot)
admin.site.register(BalanceSnapshot)
admin.site.register(InviteChainEvent)