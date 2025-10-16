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

class Location(models.Model):
    name = models.CharField(max_length=100)
    floor = models.IntegerField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='locations/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # New fields for routing
    connections = models.ManyToManyField('self', symmetrical=False, through='LocationConnection', related_name='connected_locations')
    is_transition = models.BooleanField(default=False)  # e.g., stairs, elevator
    transition_type = models.CharField(max_length=20, choices=(('corridor', 'Corridor'), ('stairs', 'Stairs'), ('elevator', 'Elevator')), null=True, blank=True)

    def __str__(self):
        return f"{self.name} (Floor {self.floor})"

class LocationConnection(models.Model):
    from_location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='outgoing_connections')
    to_location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='incoming_connections')
    weight = models.FloatField(default=1.0)  # Distance or cost (e.g., time, steps)
    transition_type = models.CharField(max_length=20, choices=(('corridor', 'Corridor'), ('stairs', 'Stairs'), ('elevator', 'Elevator')), default='corridor')

    class Meta:
        unique_together = ('from_location', 'to_location')

    def __str__(self):
        return f"{self.from_location} -> {self.to_location} ({self.transition_type})"

class LostAndFound(models.Model):
    ITEM_TYPES = (
        ('lost', 'Lost'),
        ('found', 'Found'),
    )
    CATEGORIES = (
        ('electronics', 'Electronics'),
        ('clothing', 'Clothing'),
        ('books', 'Books'),
        ('personal', 'Personal Items'),
        ('other', 'Other'),
    )
    user = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, null=True, blank=True)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    description = models.TextField()
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='Open')

    def __str__(self):
        user = self.user or self.teacher
        return f"{self.item_type.capitalize()} - {self.description[:50]} by {user.name}"