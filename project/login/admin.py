from django.contrib import admin
from .models import Student, Teacher, Product, CartItem, Order, ReturnRequest

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'student_id', 'phone_number', 'is_otp_verified')
    search_fields = ('name', 'email', 'student_id')

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'teacher_id', 'department', 'phone_number', 'is_approved', 'is_otp_verified')
    list_filter = ('is_approved', 'is_otp_verified')
    search_fields = ('name', 'email', 'teacher_id')
    actions = ['approve_teachers']

    def approve_teachers(self, request, queryset):
        queryset.update(is_approved=True)
    approve_teachers.short_description = "Approve selected teachers"

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'description')
    search_fields = ('name', 'description')

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'student', 'teacher', 'created_at')
    list_filter = ('student', 'teacher')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'student', 'total_amount', 'payment_method', 'status', 'created_at')
    list_filter = ('status', 'payment_method')
    search_fields = ('transaction_id', 'student__name')
    actions = ['approve_orders']

    def approve_orders(self, request, queryset):
        queryset.update(status='Approved')
    approve_orders.short_description = "Approve selected orders"

@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ('order', 'reason', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('order__transaction_id', 'reason')