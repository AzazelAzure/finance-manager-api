from django.apps import AppConfig

class FinanceConfig(AppConfig):
    name = "finance"

    def ready(self):
        import finance.api_tools.signals
