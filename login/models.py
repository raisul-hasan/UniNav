from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

class Student(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    student_id = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=15)
    password = models.CharField(max_length=128)
    is_otp_verified = models.BooleanField(default=False)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.name

class Teacher(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    teacher_id = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    password = models.CharField(max_length=128)
    is_approved = models.BooleanField(default=False)
    is_otp_verified = models.BooleanField(default=False)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', null=True, blank=True)

    def __str__(self):
        return self.name

class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        user = self.student or self.teacher
        return f"{user.name}'s cart: {self.product.name} x{self.quantity}"

class Order(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    cart_items = models.ManyToManyField(CartItem)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.transaction_id} by {self.student.name}"

class ReturnRequest(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    reason = models.TextField()
    status = models.CharField(max_length=20, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Return request for Order {self.order.transaction_id}"

class Group(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(Student, related_name='groups')
    teacher_members = models.ManyToManyField(Teacher, related_name='groups', blank=True)

    def __str__(self):
        return self.name

class Message(models.Model):
    sender = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='sent_messages', null=True, blank=True)
    teacher_sender = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='sent_messages', null=True, blank=True)
    recipient = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    content = models.TextField(blank=True)
    file = models.FileField(upload_to='attachments/', null=True, blank=True)
    voice = models.FileField(upload_to='voice/', null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        sender = self.sender or self.teacher_sender
        if self.group:
            return f"{sender.name} in {self.group.name}: {self.content[:50]}"
        return f"{sender.name} to {self.recipient.name}: {self.content[:50]}"

class Reaction(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, null=True, blank=True)
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user', 'teacher', 'emoji')

    def __str__(self):
        user = self.user or self.teacher
        return f"{user.name} reacted {self.emoji} to message {self.message.id}"
    
class LostFoundItem(models.Model):
    STATUS_CHOICES = [
        ("LOST", "Lost"),
        ("FOUND", "Found"),
        ("CLAIMED", "Claimed"),
    ]
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to="lostfound/", null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="LOST")

    # Where the item was found (if known). We store WGS84 coordinates for Leaflet.
    found_lat = models.FloatField(null=True, blank=True)
    found_lng = models.FloatField(null=True, blank=True)
    found_at = models.DateTimeField(null=True, blank=True)

    # Who reported
    reporter_student = models.ForeignKey(Student, null=True, blank=True, on_delete=models.SET_NULL)
    reporter_teacher = models.ForeignKey(Teacher, null=True, blank=True, on_delete=models.SET_NULL, related_name="reported_items")

    created_at = models.DateTimeField(auto_now_add=True)

    # Optional simple question prompt that claimants must answer
    claim_question = models.CharField(
        max_length=200,
        default="Describe a unique detail (e.g., color/marking) to verify ownership:"
    )
    correct_answer = models.CharField(max_length=200, blank=True, help_text="Optional exact answer; leave blank if staff will review manually.")

    def __str__(self):
        return f"{self.title} [{self.status}]"


class Claim(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]
    item = models.ForeignKey(LostFoundItem, on_delete=models.CASCADE, related_name="claims")
    claimant_student = models.ForeignKey(Student, null=True, blank=True, on_delete=models.SET_NULL)
    claimant_teacher = models.ForeignKey(Teacher, null=True, blank=True, on_delete=models.SET_NULL, related_name="claims_made")
    answer_text = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        who = self.claimant_student or self.claimant_teacher
        return f"Claim for {self.item.title} by {getattr(who, 'name', 'Unknown')} [{self.status}]"    