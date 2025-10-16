from django.contrib import admin
from .models import Claim, LostFoundItem, Student, Teacher, Product, CartItem, Order, ReturnRequest, Message, Reaction, Group

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

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'teacher_sender', 'recipient', 'group', 'content', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('content',)

@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('message', 'user', 'teacher', 'emoji', 'created_at')
    list_filter = ('emoji', 'created_at')
    search_fields = ('emoji',)

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    filter_horizontal = ('members',)

@admin.register(LostFoundItem)
class LostFoundItemAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "found_at", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "description")

@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ("item", "status", "created_at", "reviewed_at")
    list_filter = ("status",)
    search_fields = ("item__title", "answer_text")    