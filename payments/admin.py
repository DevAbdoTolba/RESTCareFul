from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'appointment', 'patient', 'amount', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('patient__email', 'paypal_order_id', 'paypal_capture_id')
    raw_id_fields = ('appointment', 'patient', 'doctor')
    readonly_fields = ('paypal_order_id', 'paypal_capture_id', 'created_at', 'updated_at')
