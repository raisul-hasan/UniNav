from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('login', '0002_product_cartitem'),  # Depends on Product and CartItem creation
        ('login', '0003_teacher_student_is_otp_verified'),  # Depends on is_otp_verified fields
    ]

    operations = [
        # No operations needed, as this is a merge migration
    ]