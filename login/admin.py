from django.contrib import admin
from .models import Claim, LostFoundItem, Student, Teacher, Product, CartItem, Order, ReturnRequest, Message, Reaction, Group,LostFoundItem, Claim
from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html
from django.db.models import Q


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




# --- SAFETY: Unregister if already registered (prevents AlreadyRegistered error)
from django.contrib.admin.sites import NotRegistered
for m in (LostFoundItem, Claim):
    try:
        admin.site.unregister(m)
    except NotRegistered:
        pass


# --- CUSTOM FILTERS ----------------------------------------------------

class HasCoordinatesFilter(admin.SimpleListFilter):
    title = "Has coordinates"
    parameter_name = "has_coords"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Yes"),
            ("no", "No"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.exclude(found_lat__isnull=True).exclude(found_lng__isnull=True)
        if self.value() == "no":
            return queryset.filter(Q(found_lat__isnull=True) | Q(found_lng__isnull=True))
        return queryset


class ClaimStatusFilter(admin.SimpleListFilter):
    title = "Claim status"
    parameter_name = "claim_status"

    def lookups(self, request, model_admin):
        return (
            ("pending", "Has PENDING"),
            ("approved", "Has APPROVED"),
            ("rejected", "Has REJECTED"),
            ("none", "No claims"),
        )

    def queryset(self, request, queryset):
        if self.value() == "pending":
            return queryset.filter(claims__status="PENDING").distinct()
        if self.value() == "approved":
            return queryset.filter(claims__status="APPROVED").distinct()
        if self.value() == "rejected":
            return queryset.filter(claims__status="REJECTED").distinct()
        if self.value() == "none":
            return queryset.filter(claims__isnull=True)
        return queryset


# --- INLINE DISPLAY FOR CLAIMS ----------------------------------------

class ClaimInline(admin.TabularInline):
    model = Claim
    extra = 0
    fields = ("claimant_display", "status", "answer_text", "created_at", "reviewed_at")
    readonly_fields = ("claimant_display", "created_at", "reviewed_at", "answer_text")

    def claimant_display(self, obj):
        who = obj.claimant_student or obj.claimant_teacher
        return getattr(who, "name", "Unknown")
    claimant_display.short_description = "Claimant"


# --- ITEM ACTIONS ------------------------------------------------------

@admin.action(description="Mark selected items as LOST")
def mark_as_lost(modeladmin, request, queryset):
    updated = queryset.update(status="LOST")
    modeladmin.message_user(request, f"Marked {updated} item(s) as LOST.", messages.SUCCESS)

@admin.action(description="Mark selected items as FOUND")
def mark_as_found(modeladmin, request, queryset):
    now = timezone.now()
    updated = 0
    for item in queryset:
        item.status = "FOUND"
        if not item.found_at:
            item.found_at = now
        item.save(update_fields=["status", "found_at"])
        updated += 1
    modeladmin.message_user(request, f"Marked {updated} item(s) as FOUND.", messages.SUCCESS)

@admin.action(description="Mark selected items as CLAIMED")
def mark_as_claimed(modeladmin, request, queryset):
    updated = queryset.update(status="CLAIMED")
    modeladmin.message_user(request, f"Marked {updated} item(s) as CLAIMED.", messages.SUCCESS)

@admin.action(description="Clear found location (lat/lng)")
def clear_location(modeladmin, request, queryset):
    updated = queryset.update(found_lat=None, found_lng=None)
    modeladmin.message_user(request, f"Cleared location for {updated} item(s).", messages.SUCCESS)


# --- LOST & FOUND ITEM ADMIN ------------------------------------------

@admin.register(LostFoundItem)
class LostFoundItemAdmin(admin.ModelAdmin):
    list_display = (
        "title", "status", "has_coords_badge", "found_at",
        "reported_by", "created_at", "quick_view_on_map",
    )
    list_filter = ("status", HasCoordinatesFilter, "created_at", "found_at", ClaimStatusFilter)
    search_fields = ("title", "description", "reporter_student__name", "reporter_teacher__name")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    inlines = [ClaimInline]
    readonly_fields = ("created_at",)
    actions = [mark_as_lost, mark_as_found, mark_as_claimed, clear_location]

    fieldsets = (
        ("Item", {
            "fields": ("title", "description", "photo", "status", "created_at")
        }),
        ("Found details", {
            "fields": ("found_at", "found_lat", "found_lng"),
            "description": "Set coordinates/time if the item is FOUND."
        }),
        ("Reporter", {
            "fields": ("reporter_student", "reporter_teacher")
        }),
        ("Claim Verification", {
            "fields": ("claim_question", "correct_answer"),
            "description": "If 'Correct Answer' is set, matching claims auto-approve."
        }),
    )

    def has_coords_badge(self, obj):
        ok = obj.found_lat is not None and obj.found_lng is not None
        color = "#28a745" if ok else "#6c757d"
        text = "Yes" if ok else "No"
        return format_html(
            '<span style="padding:2px 8px;border-radius:10px;background:{};color:#fff;font-size:12px;">{}</span>',
            color, text)
    has_coords_badge.short_description = "Has coords"

    def reported_by(self, obj):
        who = obj.reporter_student or obj.reporter_teacher
        return getattr(who, "name", "Unknown")

    def quick_view_on_map(self, obj):
        if not obj.found_lat or not obj.found_lng:
            return "-"
        url = f"https://www.openstreetmap.org/?mlat={obj.found_lat}&mlon={obj.found_lng}#map=19/{obj.found_lat}/{obj.found_lng}"
        return format_html('<a href="{}" target="_blank">Open Map</a>', url)
    quick_view_on_map.short_description = "Map"


# --- CLAIM ACTIONS -----------------------------------------------------

@admin.action(description="APPROVE selected claims")
def approve_claims(modeladmin, request, queryset):
    approved = 0
    skipped = 0
    for claim in queryset.select_related("item"):
        item = claim.item
        if item.status == "CLAIMED":
            skipped += 1
            continue
        claim.status = "APPROVED"
        claim.reviewed_at = timezone.now()
        claim.save(update_fields=["status", "reviewed_at"])
        # Reject others
        Claim.objects.filter(item=item, status="PENDING").exclude(pk=claim.pk).update(
            status="REJECTED", reviewed_at=timezone.now()
        )
        item.status = "CLAIMED"
        item.save(update_fields=["status"])
        approved += 1

    if approved:
        modeladmin.message_user(request, f"Approved {approved} claim(s).", messages.SUCCESS)
    if skipped:
        modeladmin.message_user(request, f"Skipped {skipped} (already claimed).", messages.WARNING)


@admin.action(description="REJECT selected claims")
def reject_claims(modeladmin, request, queryset):
    updated = queryset.filter(~Q(status="REJECTED")).update(status="REJECTED", reviewed_at=timezone.now())
    modeladmin.message_user(request, f"Rejected {updated} claim(s).", messages.SUCCESS)


# --- CLAIM ADMIN -------------------------------------------------------

@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ("item", "claimant_display", "status", "created_at", "reviewed_at", "answer_excerpt")
    list_filter = ("status", "created_at", "reviewed_at")
    search_fields = (
        "item__title",
        "answer_text",
        "claimant_student__name",
        "claimant_teacher__name",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    actions = [approve_claims, reject_claims]
    readonly_fields = ("created_at", "reviewed_at")

    fields = ("item", "claimant_student", "claimant_teacher", "answer_text", "status", "created_at", "reviewed_at")

    def claimant_display(self, obj):
        who = obj.claimant_student or obj.claimant_teacher
        return getattr(who, "name", "Unknown")
    claimant_display.short_description = "Claimant"

    def answer_excerpt(self, obj):
        text = (obj.answer_text or "").strip()
        return (text[:60] + "…") if len(text) > 60 else text
    answer_excerpt.short_description = "Answer"
