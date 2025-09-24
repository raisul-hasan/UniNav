from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Student, Teacher, Product, CartItem, Order, ReturnRequest
from .utils import generate_otp, send_otp_email
import random
from decimal import Decimal, InvalidOperation

# Handle user registration (student or teacher)
def register(request):
    if request.method == "POST":
        user_type = request.POST['user_type']
        name = request.POST['name']
        email = request.POST['email']
        id_number = request.POST['id_number']
        department = request.POST.get('department', '')
        phone = request.POST['phone_number']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("register")

        if Student.objects.filter(email=email).exists() or Teacher.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("register")

        if user_type == "student":
            if Student.objects.filter(student_id=id_number).exists():
                messages.error(request, "Student ID already registered")
                return redirect("register")
            user = Student(name=name, email=email, student_id=id_number, phone_number=phone)
            user.set_password(password)
            user.save()
            messages.success(request, "Registered successfully! Please login.")
            return redirect("login")
        elif user_type == "teacher":
            if Teacher.objects.filter(teacher_id=id_number).exists():
                messages.error(request, "Teacher ID already registered")
                return redirect("register")
            user = Teacher(name=name, email=email, teacher_id=id_number, department=department, phone_number=phone)
            user.set_password(password)
            user.save()
            messages.success(request, "Registration submitted! Await admin approval.")
            return redirect("login")

    return render(request, "login/register.html")

def login_request(request):
    if request.method == "POST":
        email = request.POST['email']
        password = request.POST['password']
        user_type = request.POST['user_type']

        try:
            if user_type == "student":
                user = Student.objects.get(email=email)
                if not user.is_otp_verified:
                    if user.check_password(password):
                        request.session['user_id'] = user.id
                        request.session['user_type'] = 'student'
                        messages.success(request, "Login successful! Please verify OTP.")
                        otp = generate_otp()
                        request.session['otp'] = otp
                        send_otp_email(email, otp)
                        return redirect("verify_otp")
                    else:
                        messages.error(request, "Invalid password.")
                else:
                    if user.check_password(password):
                        request.session['user_id'] = user.id
                        request.session['user_type'] = 'student'
                        messages.success(request, "Login successful!")
                        return redirect("dashboard")
                    else:
                        messages.error(request, "Invalid password.")
            elif user_type == "teacher":
                user = Teacher.objects.get(email=email)
                if not user.is_approved:
                    messages.error(request, "Your account is pending admin approval.")
                    return redirect("login")
                if not user.is_otp_verified:
                    if user.check_password(password):
                        request.session['user_id'] = user.id
                        request.session['user_type'] = 'teacher'
                        messages.success(request, "Login successful! Please verify OTP.")
                        otp = generate_otp()
                        request.session['otp'] = otp
                        send_otp_email(email, otp)
                        return redirect("verify_otp")
                    else:
                        messages.error(request, "Invalid password.")
                else:
                    if user.check_password(password):
                        request.session['user_id'] = user.id
                        request.session['user_type'] = 'teacher'
                        messages.success(request, "Login successful!")
                        return redirect("dashboard")
                    else:
                        messages.error(request, "Invalid password.")
            else:
                messages.error(request, "Invalid user type.")
        except (Student.DoesNotExist, Teacher.DoesNotExist):
            messages.error(request, "User with this email does not exist.")
        return redirect("login")
    
    return render(request, "login/login.html")

def verify_otp(request):
    if request.method == "POST":
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        entered_otp = request.POST['otp']
        stored_otp = request.session.get('otp')

        if not user_id or not user_type:
            messages.error(request, "Session expired. Please login again.")
            return redirect("login")

        try:
            if user_type == "student":
                user = Student.objects.get(id=user_id)
            elif user_type == "teacher":
                user = Teacher.objects.get(id=user_id)
            else:
                messages.error(request, "Invalid user type.")
                return redirect("login")

            if entered_otp == stored_otp:
                user.is_otp_verified = True
                user.save()
                messages.success(request, "OTP verified successfully!")
                return redirect("dashboard")
            else:
                messages.error(request, "Invalid OTP.")
                return redirect("verify_otp")
        except (Student.DoesNotExist, Teacher.DoesNotExist):
            messages.error(request, "User does not exist.")
            return redirect("login")

    return render(request, "login/viewotp.html")

def dashboard(request):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')

    if not user_id or not user_type:
        messages.error(request, "Please login to access the dashboard.")
        return redirect("login")

    if user_type == "student":
        try:
            user = Student.objects.get(id=user_id)
            cart_items = CartItem.objects.filter(student=user)
            return render(request, "login/student.html", {"user": user, "cart_items": cart_items})
        except Student.DoesNotExist:
            messages.error(request, "User does not exist.")
            return redirect("login")
    elif user_type == "teacher":
        try:
            user = Teacher.objects.get(id=user_id)
            if not user.is_approved:
                messages.error(request, "Your account is pending admin approval.")
                return redirect("login")
            products = Product.objects.all()
            orders = Order.objects.filter(status='Pending')
            return render(request, "login/teacher.html", {"user": user, "products": products, "orders": orders})
        except Teacher.DoesNotExist:
            messages.error(request, "User does not exist.")
            return redirect("login")
    else:
        messages.error(request, "Invalid user type.")
        return redirect("login")

def shop(request):
    products = Product.objects.all()
    return render(request, "login/shop.html", {"products": products})

def add_to_cart(request, product_id):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')

    if not user_id or not user_type:
        messages.error(request, "Please login to add items to cart.")
        return redirect("login")

    try:
        product = Product.objects.get(id=product_id)
        if user_type == "student":
            user = Student.objects.get(id=user_id)
            cart_item, created = CartItem.objects.get_or_create(
                product=product, student=user, defaults={'quantity': 1}
            )
            if not created:
                cart_item.quantity += 1
                cart_item.save()
        elif user_type == "teacher":
            user = Teacher.objects.get(id=user_id)
            if not user.is_approved:
                messages.error(request, "Your account is pending admin approval.")
                return redirect("login")
            cart_item, created = CartItem.objects.get_or_create(
                product=product, teacher=user, defaults={'quantity': 1}
            )
            if not created:
                cart_item.quantity += 1
                cart_item.save()
        else:
            messages.error(request, "Invalid user type.")
            return redirect("login")
        messages.success(request, "Item added to cart!")
        return redirect("shop")
    except Product.DoesNotExist:
        messages.error(request, "Product does not exist.")
        return redirect("shop")
    except (Student.DoesNotExist, Teacher.DoesNotExist):
        messages.error(request, "User does not exist.")
        return redirect("login")

def cart(request):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')

    if not user_id or not user_type:
        messages.error(request, "Please login to view cart.")
        return redirect("login")

    try:
        if user_type == "student":
            user = Student.objects.get(id=user_id)
            cart_items = CartItem.objects.filter(student=user)
        elif user_type == "teacher":
            user = Teacher.objects.get(id=user_id)
            if not user.is_approved:
                messages.error(request, "Your account is pending admin approval.")
                return redirect("login")
            cart_items = CartItem.objects.filter(teacher=user)
        else:
            messages.error(request, "Invalid user type.")
            return redirect("login")

        total_price = sum(item.product.price * item.quantity for item in cart_items)
        return render(request, "login/cart.html", {"cart_items": cart_items, "total_price": total_price})
    except (Student.DoesNotExist, Teacher.DoesNotExist):
        messages.error(request, "User does not exist.")
        return redirect("login")

def remove_from_cart(request, cart_item_id):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')

    if not user_id or not user_type:
        messages.error(request, "Please login to remove items from cart.")
        return redirect("login")

    try:
        cart_item = CartItem.objects.get(id=cart_item_id)
        if user_type == "student" and cart_item.student_id == user_id:
            cart_item.delete()
        elif user_type == "teacher" and cart_item.teacher_id == user_id:
            if not Teacher.objects.get(id=user_id).is_approved:
                messages.error(request, "Your account is pending admin approval.")
                return redirect("login")
            cart_item.delete()
        else:
            messages.error(request, "Unauthorized action.")
            return redirect("cart")
        messages.success(request, "Item removed from cart!")
        return redirect("cart")
    except CartItem.DoesNotExist:
        messages.error(request, "Cart item does not exist.")
        return redirect("cart")
    except Teacher.DoesNotExist:
        messages.error(request, "User does not exist.")
        return redirect("login")

def add_product(request):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')

    if not user_id or user_type != "teacher":
        messages.error(request, "Only approved teachers can add products.")
        return redirect("login")

    try:
        user = Teacher.objects.get(id=user_id)
        if not user.is_approved:
            messages.error(request, "Your account is pending admin approval.")
            return redirect("login")

        if request.method == "POST":
            name = request.POST['name']
            description = request.POST['description']
            try:
                price = Decimal(request.POST['price'])
            except InvalidOperation:
                messages.error(request, "Invalid price format.")
                return redirect("dashboard")
            image = request.FILES.get('image')

            Product.objects.create(
                name=name,
                description=description,
                price=price,
                image=image
            )
            messages.success(request, "Product added successfully!")
            return redirect("dashboard")
    except Teacher.DoesNotExist:
        messages.error(request, "User does not exist.")
        return redirect("login")

    return redirect("dashboard")

def delete_product(request, product_id):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')

    if not user_id or user_type != "teacher":
        messages.error(request, "Only approved teachers can delete products.")
        return redirect("login")

    try:
        user = Teacher.objects.get(id=user_id)
        if not user.is_approved:
            messages.error(request, "Your account is pending admin approval.")
            return redirect("login")
        product = Product.objects.get(id=product_id)
        product.delete()
        messages.success(request, "Product deleted successfully!")
        return redirect("dashboard")
    except Product.DoesNotExist:
        messages.error(request, "Product does not exist.")
        return redirect("dashboard")
    except Teacher.DoesNotExist:
        messages.error(request, "User does not exist.")
        return redirect("login")

def logout(request):
    request.session.flush()
    messages.success(request, "Logged out successfully!")
    return redirect("login")

def payment(request):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')

    if not user_id or user_type != "student":
        messages.error(request, "Only students can make payments.")
        return redirect("login")

    try:
        user = Student.objects.get(id=user_id)
        cart_items = CartItem.objects.filter(student=user)
        if not cart_items:
            messages.error(request, "Your cart is empty.")
            return redirect("cart")

        total_price = sum(item.product.price * item.quantity for item in cart_items)
        if request.method == "POST":
            payment_method = request.POST['payment_method']
            transaction_id = f"TXN{random.randint(100000, 999999)}"
            order = Order.objects.create(
                student=user,
                total_amount=total_price,
                payment_method=payment_method,
                transaction_id=transaction_id,
                status='Pending'
            )
            order.cart_items.set(cart_items)
            order.save()
            cart_items.delete()
            messages.success(request, "Payment request submitted! Awaiting teacher approval.")
            return redirect("payment_success", order_id=order.id)
        return render(request, "login/payment.html", {"total_price": total_price})
    except Student.DoesNotExist:
        messages.error(request, "User does not exist.")
        return redirect("login")

def process_payment(request):
    if request.method == "POST":
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        if not user_id or user_type != "student":
            messages.error(request, "Only students can process payments.")
            return redirect("login")

        try:
            user = Student.objects.get(id=user_id)
            cart_items = CartItem.objects.filter(student=user)
            if not cart_items:
                messages.error(request, "Your cart is empty.")
                return redirect("cart")
            total_price = sum(item.product.price * item.quantity for item in cart_items)
            payment_method = request.POST['payment_method']
            transaction_id = f"TXN{random.randint(100000, 999999)}"
            order = Order.objects.create(
                student=user,
                total_amount=total_price,
                payment_method=payment_method,
                transaction_id=transaction_id,
                status='Pending'
            )
            order.cart_items.set(cart_items)
            order.save()
            cart_items.delete()
            return redirect("payment_success", order_id=order.id)
        except Student.DoesNotExist:
            messages.error(request, "User does not exist.")
            return redirect("login")
        except Exception as e:
            messages.error(request, f"Payment failed: {str(e)}")
            return redirect("payment_failure")
    return redirect("cart")

def payment_success(request, order_id):
    try:
        user_id = request.session.get('user_id')
        order = Order.objects.get(id=order_id, student_id=user_id)
        return render(request, "login/payment_success.html", {"order": order})
    except Order.DoesNotExist:
        messages.error(request, "Invalid order.")
        return redirect("dashboard")

def payment_failure(request):
    return render(request, "login/payment_failure.html")

def return_request(request):
    if request.method == "POST":
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        if not user_id or user_type != "student":
            messages.error(request, "Only students can request returns.")
            return redirect("login")

        order_id = request.POST.get('order_id')
        reason = request.POST.get('reason')

        try:
            order = Order.objects.get(id=order_id, student_id=user_id)
            ReturnRequest.objects.create(order=order, reason=reason)
            messages.success(request, "Return request submitted successfully!")
            return redirect("payment_success", order_id=order.id)
        except Order.DoesNotExist:
            messages.error(request, "Invalid order.")
            return redirect("payment")
    return redirect("payment_success")

def approve_orders(request):
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    if not user_id or user_type != "teacher":
        messages.error(request, "Only approved teachers can approve orders.")
        return redirect("login")

    user = Teacher.objects.get(id=user_id)
    if not user.is_approved:
        messages.error(request, "Your account is pending admin approval.")
        return redirect("login")

    if request.method == "POST":
        order_ids = request.POST.getlist('order_ids')
        try:
            orders = Order.objects.filter(id__in=order_ids, status='Pending')
            updated_count = orders.update(status='Approved')
            messages.success(request, f"{updated_count} order(s) approved successfully!")
        except Exception as e:
            messages.error(request, f"Failed to approve orders: {str(e)}")
        return redirect("dashboard")
    return redirect("dashboard")